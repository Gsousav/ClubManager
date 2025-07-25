from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, date
from app.extensions import db
from app.models import Player, Match, MatchAttendance

matches_bp = Blueprint('matches', __name__, url_prefix='/matches')

@matches_bp.route('/')
def list_matches():
    matches = Match.query.order_by(Match.date.desc()).all()
    return render_template('matches.html', matches=matches)

@matches_bp.route('/create', methods=['GET', 'POST'])
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
        return redirect(url_for('matches.list_matches'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    today = date.today().strftime('%Y-%m-%d')
    return render_template('create_match.html', players=players, today=today)

@matches_bp.route('/edit/<int:match_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('matches.list_matches'))
    
    players = Player.query.order_by(Player.id.desc()).all()
    # Get currently selected players for this match
    attending_player_ids = [att.player_id for att in match.attendances]
    return render_template('edit_match.html', match=match, players=players, attending_player_ids=attending_player_ids)

@matches_bp.route('/delete/<int:match_id>', methods=['POST'])
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
    
    return redirect(url_for('matches.list_matches')) 