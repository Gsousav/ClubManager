from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import csv
import io
import os
import pandas as pd
from werkzeug.utils import secure_filename
import openpyxl

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = '299e44d335ce23f70d0b11c4e36388e37d2146dc591e487d'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(DATA_DIR, 'cricket.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_member = db.Column(db.Boolean, default=True)
    contact_info = db.Column(db.String(200))
    membership_fee = db.Column(db.Float, default=200.0)  # Standard membership fee for all members
    historical_match_fees_owed = db.Column(db.Float, default=0.0)  # Historical match fees owed from imports
    membership_status = db.Column(db.String(50), default='Paid')  # Unpaid, Part Paid, Paid, Sponsorship
    payments = db.relationship('Payment', backref='player', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('MatchAttendance', backref='player', lazy=True, cascade='all, delete-orphan')

    def total_paid(self):
        return sum(p.amount for p in self.payments)

    def total_owed(self):
        # Calculate match fees: members pay standard rate, non-members pay double
        match_fees = 0
        for attendance in self.attendances:
            if self.is_member:
                match_fees += attendance.match.fee
            else:
                match_fees += attendance.match.fee * 2  # Non-members pay double
        
        membership_owed = self.membership_fee if self.is_member else 0
        historical_owed = self.historical_match_fees_owed or 0
        return match_fees + membership_owed + historical_owed

    def balance(self):
        return self.total_owed() - self.total_paid()

    def is_overdue(self):
        return self.balance() > 0
    
    def membership_balance(self):
        """Calculate membership-specific balance"""
        if not self.is_member:
            return 0
        membership_paid = sum(p.amount for p in self.payments if p.payment_type == 'membership')
        return self.membership_fee - membership_paid
    
    def match_fees_owed(self):
        """Calculate total match fees owed"""
        match_fees = 0
        for attendance in self.attendances:
            if self.is_member:
                match_fees += attendance.match.fee
            else:
                match_fees += attendance.match.fee * 2  # Non-members pay double
        return match_fees
    
    def match_fees_paid(self):
        """Calculate total match fees paid"""
        return sum(p.amount for p in self.payments if p.payment_type == 'match_fee')
    
    def match_fees_balance(self):
        """Calculate match fees balance"""
        return self.match_fees_owed() - self.match_fees_paid()

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))  # Optional match name, defaults to formatted date
    date = db.Column(db.Date, default=date.today)
    fee = db.Column(db.Float, default=10.0)
    attendances = db.relationship('MatchAttendance', backref='match', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='match', lazy=True, cascade='all, delete-orphan')
    
    def display_name(self):
        """Return the match name or formatted date if no name is set"""
        return self.name or self.date.strftime('%B %d, %Y')

class MatchAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)  # null for non-match payments
    date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20))  # 'cash', 'bank'
    payment_type = db.Column(db.String(20), default='match_fee')  # 'match_fee', 'membership', 'other'

# Routes
@app.route('/')
def index():
    players = Player.query.order_by(Player.id.desc()).all()
    total_players = len(players)
    total_dues = sum(p.balance() for p in players)
    overdue_count = len([p for p in players if p.is_overdue()])
    
    return render_template('index.html', 
                         players=players, 
                         total_players=total_players,
                         total_dues=total_dues,
                         overdue_count=overdue_count)

@app.route('/players')
def players():
    players = Player.query.order_by(Player.id.desc()).all()
    return render_template('players.html', players=players)

@app.route('/players/add', methods=['GET', 'POST'])
def add_player():
    if request.method == 'POST':
        name = request.form['name']
        is_member = 'is_member' in request.form
        contact_info = request.form.get('contact_info', '')
        membership_fee = float(request.form.get('membership_fee', 200.0))
        membership_status = request.form.get('membership_status', 'Paid')
        
        player = Player(
            name=name, 
            is_member=is_member, 
            contact_info=contact_info,
            membership_fee=membership_fee,
            membership_status=membership_status
        )
        db.session.add(player)
        db.session.flush()  # Get the player ID
        
        # If membership status is "Paid", create a membership payment for the full amount
        if is_member and membership_status == 'Paid' and membership_fee > 0:
            membership_payment = Payment(
                player_id=player.id,
                amount=membership_fee,
                method='other',
                payment_type='membership',
                date=datetime.utcnow()
            )
            db.session.add(membership_payment)
        
        db.session.commit()
        flash('Player added successfully!', 'success')
        return redirect(url_for('players'))
    
    return render_template('add_player.html')

@app.route('/players/delete/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    try:
        # Get player name for the success message
        player_name = player.name
        
        # Count related records for informational purposes
        payment_count = len(player.payments)
        attendance_count = len(player.attendances)
        
        # Delete the player (this will cascade to payments and attendances)
        db.session.delete(player)
        db.session.commit()
        
        # Informative success message
        message = f'Player "{player_name}" deleted successfully!'
        if payment_count > 0 or attendance_count > 0:
            message += f' (Removed {payment_count} payment(s) and {attendance_count} attendance record(s))'
        
        flash(message, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting player: {str(e)}', 'error')
    
    return redirect(url_for('players'))

@app.route('/players/edit/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if request.method == 'POST':
        old_membership_status = player.membership_status
        old_membership_fee = player.membership_fee
        
        player.name = request.form['name']
        player.is_member = 'is_member' in request.form
        player.contact_info = request.form.get('contact_info', '')
        player.membership_fee = float(request.form.get('membership_fee', player.membership_fee))
        new_membership_status = request.form.get('membership_status', player.membership_status)
        player.membership_status = new_membership_status
        
        # If membership status changed to "Paid" and player is a member, create/adjust payment
        if (player.is_member and new_membership_status == 'Paid' and 
            old_membership_status != 'Paid' and player.membership_fee > 0):
            
            # Calculate how much membership payment is needed
            current_membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
            payment_needed = player.membership_fee - current_membership_paid
            
            if payment_needed > 0:
                # Create a payment to complete the membership
                membership_payment = Payment(
                    player_id=player.id,
                    amount=payment_needed,
                    method='other',
                    payment_type='membership',
                    date=datetime.utcnow()
                )
                db.session.add(membership_payment)
        
        db.session.commit()
        flash('Player updated successfully!', 'success')
        return redirect(url_for('players'))
    return render_template('edit_player.html', player=player)

@app.route('/players/import', methods=['GET', 'POST'])
def import_players():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.xlsx'):
            try:
                # Read the Excel file
                df = pd.read_excel(file)
                
                # Determine the format based on columns
                imported_count = 0
                errors = []
                
                # Check if it's the "Player/Subs Due/Subs Outstanding" balance sheet format (new format)
                if 'Player' in df.columns and 'Subs Due' in df.columns and 'Subs Outstanding' in df.columns:
                    for _, row in df.iterrows():
                        if pd.notna(row['Player']):
                            try:
                                name = str(row['Player']).strip()
                                
                                # Parse Member status
                                member_status = str(row['Member']).strip() if pd.notna(row['Member']) else 'Yes'
                                is_member = member_status.lower() in ['yes', 'true', '1', 'y', 'part paid']
                                
                                # Parse individual Subs Due (individual subscription fee for this player)
                                subs_due_raw = row['Subs Due'] if pd.notna(row['Subs Due']) else 0
                                if isinstance(subs_due_raw, str):
                                    subs_due_clean = subs_due_raw.replace('£', '').replace('$', '').replace(',', '').strip()
                                    subs_fee_amount = float(subs_due_clean) if subs_due_clean and subs_due_clean != '' else 0.0
                                else:
                                    subs_fee_amount = float(subs_due_raw) if subs_due_raw != '' else 0.0
                                
                                # Calculate total paid from Cash + Credit + Bank columns
                                cash_amount = 0.0
                                credit_amount = 0.0
                                bank_amount = 0.0
                                
                                # Parse Cash column
                                if 'Cash' in df.columns and pd.notna(row['Cash']):
                                    cash_raw = str(row['Cash']).replace('£', '').replace('$', '').replace(',', '').strip()
                                    cash_amount = float(cash_raw) if cash_raw and cash_raw != '' else 0.0
                                
                                # Parse Credit column
                                if 'Credit' in df.columns and pd.notna(row['Credit']):
                                    credit_raw = str(row['Credit']).replace('£', '').replace('$', '').replace(',', '').strip()
                                    credit_amount = float(credit_raw) if credit_raw and credit_raw != '' else 0.0
                                
                                # Parse Bank column
                                if 'Bank' in df.columns and pd.notna(row['Bank']):
                                    bank_raw = str(row['Bank']).replace('£', '').replace('$', '').replace(',', '').strip()
                                    bank_amount = float(bank_raw) if bank_raw and bank_raw != '' else 0.0
                                
                                # Total paid is the sum of all payment methods
                                paid_amount = cash_amount + credit_amount + bank_amount
                                
                                # Handle Subs Outstanding amount (this is the balance)
                                # Positive = they have credit, Negative = they owe money
                                outstanding_raw = row['Subs Outstanding'] if pd.notna(row['Subs Outstanding']) else 0
                                if isinstance(outstanding_raw, str):
                                    # Remove currency symbols and whitespace, handle negative values
                                    outstanding_clean = outstanding_raw.replace('£', '').replace('$', '').replace(',', '').strip()
                                    if outstanding_clean.startswith('-'):
                                        outstanding_amount = -float(outstanding_clean[1:]) if outstanding_clean[1:] else 0.0
                                    else:
                                        outstanding_amount = float(outstanding_clean) if outstanding_clean and outstanding_clean != '' else 0.0
                                else:
                                    outstanding_amount = float(outstanding_raw) if outstanding_raw != '' else 0.0
                                
                                # Check if player already exists
                                existing_player = Player.query.filter_by(name=name).first()
                                
                                if existing_player:
                                    # Update existing player
                                    player = existing_player
                                    action = "Updated"
                                else:
                                    # Create new player with membership status from Excel
                                    player = Player(name=name, is_member=is_member)
                                    db.session.add(player)
                                    db.session.flush()  # Flush to get the player ID
                                    action = "Created"
                                
                                # Update player fields
                                player.is_member = is_member
                                # Keep standard membership fee (default £200 for members, £0 for non-members)
                                if is_member and member_status.lower() not in ['overseas']:
                                    player.membership_fee = 200.0  # Standard membership fee
                                else:
                                    player.membership_fee = 0.0  # No membership fee for non-members or overseas
                                
                                # Set historical match fees owed from Subs Due
                                player.historical_match_fees_owed = subs_fee_amount
                                
                                # Clear existing payments for this player to avoid duplicates
                                if existing_player:
                                    Payment.query.filter_by(player_id=player.id).delete()
                                
                                # Add separate payment records for each payment method
                                if cash_amount > 0:
                                    cash_payment = Payment(
                                        player_id=player.id,
                                        amount=cash_amount,
                                        method='cash',
                                        payment_type='match_fee',
                                        date=datetime.utcnow()
                                    )
                                    db.session.add(cash_payment)
                                
                                if credit_amount > 0:
                                    credit_payment = Payment(
                                        player_id=player.id,
                                        amount=credit_amount,
                                        method='credit',
                                        payment_type='match_fee',
                                        date=datetime.utcnow()
                                    )
                                    db.session.add(credit_payment)
                                
                                if bank_amount > 0:
                                    bank_payment = Payment(
                                        player_id=player.id,
                                        amount=bank_amount,
                                        method='bank',
                                        payment_type='match_fee',
                                        date=datetime.utcnow()
                                    )
                                    db.session.add(bank_payment)
                                
                                # Set membership status based on member status from Excel and outstanding balance
                                if member_status.lower() == 'part paid':
                                    player.membership_status = 'Part Paid'
                                elif member_status.lower() == 'overseas':
                                    player.membership_status = 'Overseas'
                                elif outstanding_amount < 0:
                                    # Negative outstanding = they owe money
                                    player.membership_status = 'Unpaid'
                                elif outstanding_amount == 0:
                                    # Zero outstanding = fully paid
                                    player.membership_status = 'Paid'
                                else:
                                    # Positive outstanding = overpaid/credit
                                    player.membership_status = 'Paid'
                                
                                # If membership status is "Paid" and player is a member, create membership payment
                                if (player.membership_status == 'Paid' and player.is_member and player.membership_fee > 0):
                                    # Check if we already have enough membership payments
                                    current_membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
                                    payment_needed = player.membership_fee - current_membership_paid
                                    
                                    if payment_needed > 0:
                                        membership_payment = Payment(
                                            player_id=player.id,
                                            amount=payment_needed,
                                            method='other',
                                            payment_type='membership',
                                            date=datetime.utcnow()
                                        )
                                        db.session.add(membership_payment)
                                
                                imported_count += 1
                                
                                # Debug info for troubleshooting
                                calculated_balance = player.balance()
                                print(f"Imported {name}: Member={member_status}, HistoricalMatchFees=£{subs_fee_amount:.2f}, MembershipFee=£{player.membership_fee:.2f}, "
                                      f"Cash=£{cash_amount:.2f}, Credit=£{credit_amount:.2f}, Bank=£{bank_amount:.2f}, "
                                      f"TotalPaid=£{paid_amount:.2f}, SubsOutstanding=£{outstanding_amount:.2f}, "
                                      f"CalculatedBalance=£{calculated_balance:.2f}, Status={player.membership_status}")
                                
                            except Exception as e:
                                errors.append(f"Error importing {row.get('Player', 'Unknown')}: {str(e)}")
                
                # Check if it's the "Matches" sheet format
                elif 'Player' in df.columns and 'Member' in df.columns:
                    for _, row in df.iterrows():
                        if pd.notna(row['Player']):
                            try:
                                name = str(row['Player']).strip()
                                is_member = str(row['Member']).strip().lower() in ['yes', 'true', '1', 'y']
                                
                                # Check if player already exists
                                existing_player = Player.query.filter_by(name=name).first()
                                if not existing_player:
                                    player = Player(name=name, is_member=is_member)
                                    db.session.add(player)
                                    db.session.flush()  # Get the player ID
                                    
                                    # Since default status is "Paid" and they're a member, create membership payment
                                    if is_member and player.membership_fee > 0:
                                        membership_payment = Payment(
                                            player_id=player.id,
                                            amount=player.membership_fee,
                                            method='other',
                                            payment_type='membership',
                                            date=datetime.utcnow()
                                        )
                                        db.session.add(membership_payment)
                                    
                                    imported_count += 1
                                else:
                                    errors.append(f"Player '{name}' already exists")
                            except Exception as e:
                                errors.append(f"Error importing {row.get('Player', 'Unknown')}: {str(e)}")
                
                # Check if it's the "Memberships" sheet format
                elif 'Name' in df.columns and 'Membership' in df.columns:
                    for _, row in df.iterrows():
                        if pd.notna(row['Name']) and pd.notna(row['Membership']):
                            try:
                                name = str(row['Name']).strip()
                                membership_fee = float(row['Membership'])
                                
                                # Determine membership status from Unnamed: 2 column
                                membership_status = 'Unpaid'
                                if 'Unnamed: 2' in df.columns and pd.notna(row['Unnamed: 2']):
                                    status_text = str(row['Unnamed: 2']).strip()
                                    if 'part paid' in status_text.lower():
                                        membership_status = 'Part Paid'
                                    elif 'sponsorship' in status_text.lower():
                                        membership_status = 'Sponsorship'
                                    elif 'paid' in status_text.lower():
                                        membership_status = 'Paid'
                                
                                # Check if player already exists
                                existing_player = Player.query.filter_by(name=name).first()
                                if not existing_player:
                                    player = Player(
                                        name=name, 
                                        is_member=True, 
                                        membership_fee=membership_fee,
                                        membership_status=membership_status
                                    )
                                    db.session.add(player)
                                    db.session.flush()  # Get the player ID
                                    
                                    # If membership status is "Paid", create a membership payment
                                    if membership_status == 'Paid' and membership_fee > 0:
                                        membership_payment = Payment(
                                            player_id=player.id,
                                            amount=membership_fee,
                                            method='other',
                                            payment_type='membership',
                                            date=datetime.utcnow()
                                        )
                                        db.session.add(membership_payment)
                                    
                                    imported_count += 1
                                else:
                                    # Update existing player's membership info
                                    old_status = existing_player.membership_status
                                    existing_player.membership_fee = membership_fee
                                    existing_player.membership_status = membership_status
                                    existing_player.is_member = True
                                    
                                    # If membership status changed to "Paid", create/adjust payment
                                    if (membership_status == 'Paid' and old_status != 'Paid' and membership_fee > 0):
                                        # Calculate how much membership payment is needed
                                        current_membership_paid = sum(p.amount for p in existing_player.payments if p.payment_type == 'membership')
                                        payment_needed = membership_fee - current_membership_paid
                                        
                                        if payment_needed > 0:
                                            membership_payment = Payment(
                                                player_id=existing_player.id,
                                                amount=payment_needed,
                                                method='other',
                                                payment_type='membership',
                                                date=datetime.utcnow()
                                            )
                                            db.session.add(membership_payment)
                                    
                                    imported_count += 1
                            except Exception as e:
                                errors.append(f"Error importing {row.get('Name', 'Unknown')}: {str(e)}")
                
                # Check if it's a simple "Name" column format
                elif 'Name' in df.columns:
                    for _, row in df.iterrows():
                        if pd.notna(row['Name']):
                            try:
                                name = str(row['Name']).strip()
                                
                                # Check if player already exists
                                existing_player = Player.query.filter_by(name=name).first()
                                if not existing_player:
                                    player = Player(name=name, is_member=True)  # Default to member
                                    db.session.add(player)
                                    db.session.flush()  # Get the player ID
                                    
                                    # Since default status is "Paid" and they're a member, create membership payment
                                    if player.membership_fee > 0:
                                        membership_payment = Payment(
                                            player_id=player.id,
                                            amount=player.membership_fee,
                                            method='other',
                                            payment_type='membership',
                                            date=datetime.utcnow()
                                        )
                                        db.session.add(membership_payment)
                                    
                                    imported_count += 1
                                else:
                                    errors.append(f"Player '{name}' already exists")
                            except Exception as e:
                                errors.append(f"Error importing {row.get('Name', 'Unknown')}: {str(e)}")
                
                # Check if it's the "Nets" sheet format
                elif 'Name' in df.columns and 'Total Due' in df.columns:
                    for _, row in df.iterrows():
                        if pd.notna(row['Name']):
                            try:
                                name = str(row['Name']).strip()
                                
                                # Check if player already exists
                                existing_player = Player.query.filter_by(name=name).first()
                                if not existing_player:
                                    player = Player(name=name, is_member=True)  # Default to member
                                    db.session.add(player)
                                    db.session.flush()  # Get the player ID
                                    
                                    # Since default status is "Paid" and they're a member, create membership payment
                                    if player.membership_fee > 0:
                                        membership_payment = Payment(
                                            player_id=player.id,
                                            amount=player.membership_fee,
                                            method='other',
                                            payment_type='membership',
                                            date=datetime.utcnow()
                                        )
                                        db.session.add(membership_payment)
                                    
                                    imported_count += 1
                                else:
                                    errors.append(f"Player '{name}' already exists")
                            except Exception as e:
                                errors.append(f"Error importing {row.get('Name', 'Unknown')}: {str(e)}")
                
                else:
                    flash('Unsupported Excel format. Supported formats: Player/Member/Subs Due/Subs Outstanding (with Cash/Credit/Bank), Player/Member, Name/Membership, or simple Name column.', 'error')
                    return redirect(request.url)
                
                db.session.commit()
                
                if imported_count > 0:
                    # Determine what was imported based on columns
                    if 'Subs Due' in df.columns and 'Subs Outstanding' in df.columns:
                        flash(f'Successfully imported {imported_count} players with historical match fees and payment records!', 'success')
                        flash('Historical match fees, membership fees, and payment records have been updated. Non-members will pay double the match fee going forward.', 'info')
                    else:
                        flash(f'Successfully imported {imported_count} players!', 'success')
                        
                if errors:
                    flash(f'Some errors occurred: {len(errors)} players could not be imported', 'warning')
                    for error in errors[:5]:  # Show first 5 errors
                        flash(error, 'error')
                
                return redirect(url_for('players'))
                
            except Exception as e:
                flash(f'Error reading Excel file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Please upload an Excel file (.xlsx)', 'error')
            return redirect(request.url)
    
    return render_template('import_players.html')

@app.route('/matches')
def matches():
    matches = Match.query.order_by(Match.date.desc()).all()
    return render_template('matches.html', matches=matches)

@app.route('/matches/create', methods=['GET', 'POST'])
def create_match():
    if request.method == 'POST':
        match_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        fee = float(request.form['fee'])
        match_name = request.form.get('name', '').strip()
        selected_players = request.form.getlist('players')
        
        # If no name provided, use formatted date as default
        if not match_name:
            match_name = match_date.strftime('%B %d, %Y')
        
        # Create match
        match = Match(name=match_name, date=match_date, fee=fee)
        db.session.add(match)
        db.session.flush()  # Get the match ID
        
        # Add attendances
        for player_id in selected_players:
            attendance = MatchAttendance(player_id=int(player_id), match_id=match.id)
            db.session.add(attendance)
        
        db.session.commit()
        flash(f'Match "{match_name}" created successfully! {len(selected_players)} players marked as attended.', 'success')
        return redirect(url_for('matches'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    today = date.today().strftime('%Y-%m-%d')
    return render_template('create_match.html', players=players, today=today)

@app.route('/matches/edit/<int:match_id>', methods=['GET', 'POST'])
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)
    if request.method == 'POST':
        match_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        fee = float(request.form['fee'])
        match_name = request.form.get('name', '').strip()
        selected_players = request.form.getlist('players')
        
        # If no name provided, use formatted date as default
        if not match_name:
            match_name = match_date.strftime('%B %d, %Y')
        
        # Update match details
        match.name = match_name
        match.date = match_date
        match.fee = fee
        
        # Remove all existing attendances
        MatchAttendance.query.filter_by(match_id=match.id).delete()
        
        # Add new attendances
        for player_id in selected_players:
            attendance = MatchAttendance(player_id=int(player_id), match_id=match.id)
            db.session.add(attendance)
        
        db.session.commit()
        flash(f'Match "{match_name}" updated successfully! {len(selected_players)} players marked as attended.', 'success')
        return redirect(url_for('matches'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    # Get currently selected players for this match
    attending_player_ids = [att.player_id for att in match.attendances]
    return render_template('edit_match.html', match=match, players=players, attending_player_ids=attending_player_ids)

@app.route('/matches/delete/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    try:
        # Get match info for the success message
        match_date = match.date.strftime('%B %d, %Y')
        attendance_count = len(match.attendances)
        payment_count = len(match.payments)
        
        # Delete the match (this will cascade to attendances and payments due to cascade='all, delete-orphan')
        db.session.delete(match)
        db.session.commit()
        
        # Informative success message
        message = f'Match from {match_date} deleted successfully!'
        if attendance_count > 0 or payment_count > 0:
            details = []
            if attendance_count > 0:
                details.append(f'{attendance_count} attendance record(s)')
            if payment_count > 0:
                details.append(f'{payment_count} payment(s)')
            message += f' (Removed {", ".join(details)})'
        
        flash(message, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting match: {str(e)}', 'error')
    
    return redirect(url_for('matches'))

@app.route('/payments')
def payments():
    payments = Payment.query.order_by(Payment.date.desc()).all()
    return render_template('payments.html', payments=payments)

@app.route('/payments/add', methods=['GET', 'POST'])
def add_payment():
    if request.method == 'POST':
        player_id = int(request.form['player_id'])
        amount = float(request.form['amount'])
        method = request.form['method']
        payment_type = request.form.get('payment_type', 'match_fee')
        payment_date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        
        # Get match_id if it's a match fee payment
        match_id = None
        if payment_type == 'match_fee' and request.form.get('match_id'):
            match_id = int(request.form['match_id'])
        
        payment = Payment(
            player_id=player_id, 
            amount=amount, 
            method=method, 
            payment_type=payment_type,
            match_id=match_id,
            date=payment_date
        )
        db.session.add(payment)
        
        # Update player's membership status if it's a membership payment
        if payment_type == 'membership':
            player = Player.query.get(player_id)
            if player and player.is_member:
                membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
                if membership_paid >= player.membership_fee:
                    player.membership_status = 'Paid'
                elif membership_paid > 0:
                    player.membership_status = 'Part Paid'
        
        db.session.commit()
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('payments'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    matches = Match.query.order_by(Match.date.desc()).all()
    today = date.today().strftime('%Y-%m-%d')
    return render_template('add_payment.html', players=players, matches=matches, today=today)

@app.route('/payments/edit/<int:payment_id>', methods=['GET', 'POST'])
def edit_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if request.method == 'POST':
        old_player_id = payment.player_id
        old_payment_type = payment.payment_type
        old_amount = payment.amount
        
        payment.player_id = int(request.form['player_id'])
        payment.amount = float(request.form['amount'])
        payment.method = request.form['method']
        payment.payment_type = request.form.get('payment_type', 'match_fee')
        payment.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        
        # Update match_id if it's a match fee payment
        if payment.payment_type == 'match_fee' and request.form.get('match_id'):
            payment.match_id = int(request.form['match_id'])
        else:
            payment.match_id = None
        
        # Update membership status for affected players
        def update_membership_status(player_id):
            player = Player.query.get(player_id)
            if player and player.is_member:
                membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
                if membership_paid >= player.membership_fee:
                    player.membership_status = 'Paid'
                elif membership_paid > 0:
                    player.membership_status = 'Part Paid'
                else:
                    player.membership_status = 'Unpaid'
        
        # Update membership status for old player if payment was membership-related
        if old_payment_type == 'membership':
            update_membership_status(old_player_id)
        
        # Update membership status for new player if payment is membership-related
        if payment.payment_type == 'membership':
            update_membership_status(payment.player_id)
        
        db.session.commit()
        flash('Payment updated successfully!', 'success')
        return redirect(url_for('payments'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    matches = Match.query.order_by(Match.date.desc()).all()
    return render_template('edit_payment.html', payment=payment, players=players, matches=matches)

@app.route('/payments/delete/<int:payment_id>', methods=['POST'])
def delete_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    try:
        player_name = payment.player.name
        amount = payment.amount
        old_player_id = payment.player_id
        old_payment_type = payment.payment_type
        
        # Delete the payment
        db.session.delete(payment)
        
        # Update membership status if it was a membership payment
        if old_payment_type == 'membership':
            player = Player.query.get(old_player_id)
            if player and player.is_member:
                membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
                if membership_paid >= player.membership_fee:
                    player.membership_status = 'Paid'
                elif membership_paid > 0:
                    player.membership_status = 'Part Paid'
                else:
                    player.membership_status = 'Unpaid'
        
        db.session.commit()
        flash(f'Payment of £{amount:.2f} for {player_name} deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting payment: {str(e)}', 'error')
    
    return redirect(url_for('payments'))

@app.route('/overdue')
def overdue():
    players = Player.query.order_by(Player.id.desc()).all()
    overdue_players = [p for p in players if p.is_overdue()]
    total_outstanding = sum(p.balance() for p in overdue_players)
    response = make_response(render_template('overdue.html', players=overdue_players, total_outstanding=total_outstanding))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/export/overdue')
def export_overdue():
    players = Player.query.order_by(Player.id.desc()).all()
    overdue_players = [p for p in players if p.is_overdue()]

    # Prepare data for DataFrame
    data = []
    for player in overdue_players:
        data.append({
            'Player Name': player.name,
            'Member Status': 'Member' if player.is_member else 'Non-Member',
            'Contact Info': player.contact_info or '',
            'Membership Fee': player.membership_fee if player.is_member else '',
            'Membership Status': player.membership_status if player.is_member else '',
            'Total Owed': player.total_owed(),
            'Total Paid': player.total_paid(),
            'Balance': player.balance(),
        })

    df = pd.DataFrame(data)

    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Overdue Balances')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'overdue_balances_{date.today()}.xlsx'
    )

@app.route('/api/player/<int:player_id>/balance')
def player_balance(player_id):
    player = Player.query.get_or_404(player_id)
    return jsonify({
        'name': player.name,
        'total_owed': player.total_owed(),
        'total_paid': player.total_paid(),
        'balance': player.balance()
    })

def migrate_database():
    """Add new columns to existing database if needed"""
    try:
        with app.app_context():
            # Check if we need to add new columns
            inspector = db.inspect(db.engine)
            
            # Check if tables exist first
            if 'player' in inspector.get_table_names():
                player_columns = [col['name'] for col in inspector.get_columns('player')]
                
                # Add missing columns to player table
                if 'membership_fee' not in player_columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE player ADD COLUMN membership_fee REAL DEFAULT 200.0'))
                        conn.commit()
                    print("✓ Added membership_fee column")
                
                if 'historical_match_fees_owed' not in player_columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE player ADD COLUMN historical_match_fees_owed REAL DEFAULT 0.0'))
                        conn.commit()
                    print("✓ Added historical_match_fees_owed column")
                
                if 'membership_status' not in player_columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE player ADD COLUMN membership_status TEXT DEFAULT "Paid"'))
                        conn.commit()
                    print("✓ Added membership_status column")
            
            if 'payment' in inspector.get_table_names():
                payment_columns = [col['name'] for col in inspector.get_columns('payment')]
                
                # Add missing columns to payment table
                if 'payment_type' not in payment_columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE payment ADD COLUMN payment_type TEXT DEFAULT "match_fee"'))
                        conn.commit()
                    print("✓ Added payment_type column")
                
                if 'match_id' not in payment_columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE payment ADD COLUMN match_id INTEGER'))
                        conn.commit()
                    print("✓ Added match_id column")
            
            if 'match' in inspector.get_table_names():
                match_columns = [col['name'] for col in inspector.get_columns('match')]
                
                # Add missing columns to match table
                if 'name' not in match_columns:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE match ADD COLUMN name TEXT'))
                        conn.commit()
                    print("✓ Added name column to match table")
                    
                    # Auto-populate names for existing matches
                    matches = Match.query.all()
                    for match in matches:
                        if not match.name:
                            match.name = match.date.strftime('%B %d, %Y')
                    db.session.commit()
                    print("✓ Auto-populated names for existing matches")
            
            # Fix existing players with "Paid" status but no membership payments
            players_with_paid_status = Player.query.filter_by(membership_status='Paid', is_member=True).all()
            for player in players_with_paid_status:
                if player.membership_fee > 0:
                    # Check if they already have membership payments
                    membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
                    payment_needed = player.membership_fee - membership_paid
                    
                    if payment_needed > 0:
                        # Create a membership payment to balance the account
                        membership_payment = Payment(
                            player_id=player.id,
                            amount=payment_needed,
                            method='other',
                            payment_type='membership',
                            date=datetime.utcnow()
                        )
                        db.session.add(membership_payment)
                        print(f"✓ Created membership payment of £{payment_needed:.2f} for {player.name}")
            
            db.session.commit()
                
    except Exception as e:
        print(f"Migration error (this is normal for new databases): {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrate_database()
    app.run(debug=True, port=8080, host='127.0.0.1')

