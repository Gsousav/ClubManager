from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime, date
import io
import pandas as pd
from app.extensions import db
from app.models import Player, Payment
from app.utils.imports import handle_excel_import

players_bp = Blueprint('players', __name__, url_prefix='/players')

@players_bp.route('/')
def list_players():
    players = Player.query.order_by(Player.id.desc()).all()
    return render_template('players.html', players=players)

@players_bp.route('/add', methods=['GET', 'POST'])
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
        return redirect(url_for('players.list_players'))
    
    return render_template('add_player.html')

@players_bp.route('/delete/<int:player_id>', methods=['POST'])
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
    
    return redirect(url_for('players.list_players'))

@players_bp.route('/edit/<int:player_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('players.list_players'))
    return render_template('edit_player.html', player=player)

@players_bp.route('/import', methods=['GET', 'POST'])
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
                imported_count, errors = handle_excel_import(file)
                
                if imported_count > 0:
                    flash(f'Successfully imported {imported_count} players!', 'success')
                        
                if errors:
                    flash(f'Some errors occurred: {len(errors)} players could not be imported', 'warning')
                    for error in errors[:5]:  # Show first 5 errors
                        flash(error, 'error')
                
                return redirect(url_for('players.list_players'))
                
            except Exception as e:
                flash(f'Error reading Excel file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Please upload an Excel file (.xlsx)', 'error')
            return redirect(request.url)
    
    return render_template('import_players.html')

@players_bp.route('/export/overdue')
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