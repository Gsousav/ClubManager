from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, date
from app.extensions import db
from app.models import Player, Match, Payment

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/')
def list_payments():
    payments = Payment.query.order_by(Payment.date.desc()).all()
    return render_template('payments.html', payments=payments)

@payments_bp.route('/add', methods=['GET', 'POST'])
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
        return redirect(url_for('payments.list_payments'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    matches = Match.query.order_by(Match.date.desc()).all()
    today = date.today().strftime('%Y-%m-%d')
    return render_template('add_payment.html', players=players, matches=matches, today=today)

@payments_bp.route('/edit/<int:payment_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('payments.list_payments'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    matches = Match.query.order_by(Match.date.desc()).all()
    return render_template('edit_payment.html', payment=payment, players=players, matches=matches)

@payments_bp.route('/delete/<int:payment_id>', methods=['POST'])
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
    
    return redirect(url_for('payments.list_payments')) 