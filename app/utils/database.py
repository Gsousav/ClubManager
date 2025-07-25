from datetime import datetime
from app.extensions import db
from app.models import Payment

def migrate_database(app):
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
                from app.models import Match
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
            from app.models import Player
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

def initialize_database(app):
    """Initialize database and run migrations"""
    with app.app_context():
        db.create_all()
        migrate_database(app) 