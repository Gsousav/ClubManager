from datetime import datetime
from app.extensions import db

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)  # null for non-match payments
    date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20))  # 'cash', 'bank'
    payment_type = db.Column(db.String(20), default='match_fee')  # 'match_fee', 'membership', 'other' 