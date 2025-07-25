from app.extensions import db

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