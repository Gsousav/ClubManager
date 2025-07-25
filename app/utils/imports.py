import pandas as pd
from datetime import datetime
from app.extensions import db
from app.models import Player, Payment

def handle_excel_import(file):
    """Handle Excel file import and return (imported_count, errors)"""
    try:
        # Read the Excel file
        df = pd.read_excel(file)
        
        imported_count = 0
        errors = []
        
        # Check if it's the "Player/Subs Due/Subs Outstanding" balance sheet format (new format)
        if 'Player' in df.columns and 'Subs Due' in df.columns and 'Subs Outstanding' in df.columns:
            imported_count, errors = _import_balance_sheet_format(df)
            
        # Check if it's the "Matches" sheet format
        elif 'Player' in df.columns and 'Member' in df.columns:
            imported_count, errors = _import_matches_format(df)
            
        # Check if it's the "Memberships" sheet format
        elif 'Name' in df.columns and 'Membership' in df.columns:
            imported_count, errors = _import_memberships_format(df)
            
        # Check if it's a simple "Name" column format
        elif 'Name' in df.columns:
            imported_count, errors = _import_simple_name_format(df)
            
        # Check if it's the "Nets" sheet format
        elif 'Name' in df.columns and 'Total Due' in df.columns:
            imported_count, errors = _import_nets_format(df)
            
        else:
            raise ValueError('Unsupported Excel format. Supported formats: Player/Member/Subs Due/Subs Outstanding (with Cash/Credit/Bank), Player/Member, Name/Membership, or simple Name column.')
        
        if imported_count > 0:
            db.session.commit()
        
        return imported_count, errors
        
    except Exception as e:
        db.session.rollback()
        raise e

def _import_balance_sheet_format(df):
    """Import from balance sheet format with Player/Subs Due/Subs Outstanding"""
    imported_count = 0
    errors = []
    
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
                cash_amount = _parse_currency_amount(row.get('Cash', 0))
                credit_amount = _parse_currency_amount(row.get('Credit', 0))
                bank_amount = _parse_currency_amount(row.get('Bank', 0))
                
                # Total paid is the sum of all payment methods
                paid_amount = cash_amount + credit_amount + bank_amount
                
                # Handle Subs Outstanding amount (this is the balance)
                outstanding_raw = row['Subs Outstanding'] if pd.notna(row['Subs Outstanding']) else 0
                outstanding_amount = _parse_currency_amount(outstanding_raw, allow_negative=True)
                
                # Check if player already exists
                existing_player = Player.query.filter_by(name=name).first()
                
                if existing_player:
                    player = existing_player
                    action = "Updated"
                else:
                    player = Player(name=name, is_member=is_member)
                    db.session.add(player)
                    db.session.flush()
                    action = "Created"
                
                # Update player fields
                player.is_member = is_member
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
                _add_payment_if_positive(player.id, cash_amount, 'cash', 'match_fee')
                _add_payment_if_positive(player.id, credit_amount, 'credit', 'match_fee')
                _add_payment_if_positive(player.id, bank_amount, 'bank', 'match_fee')
                
                # Set membership status
                _set_membership_status(player, member_status, outstanding_amount)
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error importing {row.get('Player', 'Unknown')}: {str(e)}")
    
    return imported_count, errors

def _import_matches_format(df):
    """Import from matches format with Player/Member columns"""
    imported_count = 0
    errors = []
    
    for _, row in df.iterrows():
        if pd.notna(row['Player']):
            try:
                name = str(row['Player']).strip()
                is_member = str(row['Member']).strip().lower() in ['yes', 'true', '1', 'y']
                
                existing_player = Player.query.filter_by(name=name).first()
                if not existing_player:
                    player = Player(name=name, is_member=is_member)
                    db.session.add(player)
                    db.session.flush()
                    
                    # Create membership payment if member
                    if is_member and player.membership_fee > 0:
                        _create_membership_payment(player.id, player.membership_fee)
                    
                    imported_count += 1
                else:
                    errors.append(f"Player '{name}' already exists")
            except Exception as e:
                errors.append(f"Error importing {row.get('Player', 'Unknown')}: {str(e)}")
    
    return imported_count, errors

def _import_memberships_format(df):
    """Import from memberships format with Name/Membership columns"""
    imported_count = 0
    errors = []
    
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
                
                existing_player = Player.query.filter_by(name=name).first()
                if not existing_player:
                    player = Player(
                        name=name, 
                        is_member=True, 
                        membership_fee=membership_fee,
                        membership_status=membership_status
                    )
                    db.session.add(player)
                    db.session.flush()
                    
                    # Create membership payment if paid
                    if membership_status == 'Paid' and membership_fee > 0:
                        _create_membership_payment(player.id, membership_fee)
                    
                    imported_count += 1
                else:
                    # Update existing player
                    _update_existing_player_membership(existing_player, membership_fee, membership_status)
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Error importing {row.get('Name', 'Unknown')}: {str(e)}")
    
    return imported_count, errors

def _import_simple_name_format(df):
    """Import from simple Name column format"""
    imported_count = 0
    errors = []
    
    for _, row in df.iterrows():
        if pd.notna(row['Name']):
            try:
                name = str(row['Name']).strip()
                
                existing_player = Player.query.filter_by(name=name).first()
                if not existing_player:
                    player = Player(name=name, is_member=True)
                    db.session.add(player)
                    db.session.flush()
                    
                    # Create membership payment
                    if player.membership_fee > 0:
                        _create_membership_payment(player.id, player.membership_fee)
                    
                    imported_count += 1
                else:
                    errors.append(f"Player '{name}' already exists")
            except Exception as e:
                errors.append(f"Error importing {row.get('Name', 'Unknown')}: {str(e)}")
    
    return imported_count, errors

def _import_nets_format(df):
    """Import from nets format with Name/Total Due columns"""
    imported_count = 0
    errors = []
    
    for _, row in df.iterrows():
        if pd.notna(row['Name']):
            try:
                name = str(row['Name']).strip()
                
                existing_player = Player.query.filter_by(name=name).first()
                if not existing_player:
                    player = Player(name=name, is_member=True)
                    db.session.add(player)
                    db.session.flush()
                    
                    # Create membership payment
                    if player.membership_fee > 0:
                        _create_membership_payment(player.id, player.membership_fee)
                    
                    imported_count += 1
                else:
                    errors.append(f"Player '{name}' already exists")
            except Exception as e:
                errors.append(f"Error importing {row.get('Name', 'Unknown')}: {str(e)}")
    
    return imported_count, errors

def _parse_currency_amount(value, allow_negative=False):
    """Parse currency amount from various formats"""
    if pd.isna(value) or value == '':
        return 0.0
    
    if isinstance(value, str):
        clean_value = value.replace('£', '').replace('$', '').replace(',', '').strip()
        if allow_negative and clean_value.startswith('-'):
            return -float(clean_value[1:]) if clean_value[1:] else 0.0
        else:
            return float(clean_value) if clean_value else 0.0
    else:
        return float(value) if value != '' else 0.0

def _add_payment_if_positive(player_id, amount, method, payment_type):
    """Add payment record if amount is positive"""
    if amount > 0:
        payment = Payment(
            player_id=player_id,
            amount=amount,
            method=method,
            payment_type=payment_type,
            date=datetime.utcnow()
        )
        db.session.add(payment)

def _create_membership_payment(player_id, amount):
    """Create a membership payment"""
    payment = Payment(
        player_id=player_id,
        amount=amount,
        method='other',
        payment_type='membership',
        date=datetime.utcnow()
    )
    db.session.add(payment)

def _set_membership_status(player, member_status, outstanding_amount):
    """Set player membership status based on member status and outstanding amount"""
    if member_status.lower() == 'part paid':
        player.membership_status = 'Part Paid'
    elif member_status.lower() == 'overseas':
        player.membership_status = 'Overseas'
    elif outstanding_amount < 0:
        player.membership_status = 'Unpaid'
    elif outstanding_amount == 0:
        player.membership_status = 'Paid'
    else:
        player.membership_status = 'Paid'
    
    # Create membership payment if paid and member
    if (player.membership_status == 'Paid' and player.is_member and player.membership_fee > 0):
        current_membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
        payment_needed = player.membership_fee - current_membership_paid
        
        if payment_needed > 0:
            _create_membership_payment(player.id, payment_needed)

def _update_existing_player_membership(player, membership_fee, membership_status):
    """Update existing player's membership information"""
    old_status = player.membership_status
    player.membership_fee = membership_fee
    player.membership_status = membership_status
    player.is_member = True
    
    # Create membership payment if status changed to paid
    if (membership_status == 'Paid' and old_status != 'Paid' and membership_fee > 0):
        current_membership_paid = sum(p.amount for p in player.payments if p.payment_type == 'membership')
        payment_needed = membership_fee - current_membership_paid
        
        if payment_needed > 0:
            _create_membership_payment(player.id, payment_needed) 