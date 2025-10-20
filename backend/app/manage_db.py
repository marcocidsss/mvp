from app import create_app, db
from app.models import User, Event, RoleEnum
import os
from datetime import datetime
app = create_app()
with app.app_context():
    db.create_all()
    # create default admin if not exists
    if not User.query.filter_by(email='admin@gijonclub.local').first():
        u = User(email='admin@gijonclub.local', name='Admin Gijón', role=RoleEnum.admin)
        u.set_password('AdminPass123!')
        db.session.add(u)
    if not User.query.filter_by(email='rrpp@gijonclub.local').first():
        r = User(email='rrpp@gijonclub.local', name='RRPP Gijón', role=RoleEnum.rrpp)
        r.set_password('RrppPass123!')
        db.session.add(r)
    if not User.query.filter_by(email='scanner@gijonclub.local').first():
        s = User(email='scanner@gijonclub.local', name='Scanner Gijón', role=RoleEnum.scanner)
        s.set_password('ScanPass123!')
        db.session.add(s)
    if not User.query.filter_by(email='user@gijonclub.local').first():
        u2 = User(email='user@gijonclub.local', name='User Demo', role=RoleEnum.user)
        u2.set_password('UserPass123!')
        db.session.add(u2)
    # create sample event
    if not Event.query.first():
        ev = Event(title='Noche Indie - Gijón', date=datetime.fromisoformat('2025-10-25T22:00:00'), capacity=500, zones={'pista':400,'vip':100})
        db.session.add(ev)
    db.session.commit()
    print('DB initialized and seed created.')
