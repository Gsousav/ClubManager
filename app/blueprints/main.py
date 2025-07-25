from flask import Blueprint, render_template, jsonify, make_response
from app.models import Player

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
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

@main_bp.route('/overdue')
def overdue():
    players = Player.query.order_by(Player.id.desc()).all()
    overdue_players = [p for p in players if p.is_overdue()]
    total_outstanding = sum(p.balance() for p in overdue_players)
    response = make_response(render_template('overdue.html', players=overdue_players, total_outstanding=total_outstanding))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@main_bp.route('/api/player/<int:player_id>/balance')
def player_balance(player_id):
    player = Player.query.get_or_404(player_id)
    return jsonify({
        'name': player.name,
        'total_owed': player.total_owed(),
        'total_paid': player.total_paid(),
        'balance': player.balance()
    }) 