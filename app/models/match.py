from datetime import date
from app.extensions import db

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