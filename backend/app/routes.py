from flask import Blueprint, request, jsonify, current_app, send_from_directory
from . import db
from .models import User, Event, Ticket, RoleEnum
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
import os

bp = Blueprint('routes', __name__)

# Static pages endpoints (serve frontend)
@bp.route('/')
def index():
    return send_from_directory(current_app.static_folder, 'purchase.html')

@bp.route('/admin')
def admin_page():
    return send_from_directory(current_app.static_folder, 'admin.html')

@bp.route('/scanner')
def scanner_page():
    return send_from_directory(current_app.static_folder, 'scanner.html')

# --- Auth ---
@bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email')
    name = data.get('name','')
    password = data.get('password')
    if not email or not password:
        return jsonify({'status':'error','message':'missing_fields'}),400
    if User.query.filter_by(email=email).first():
        return jsonify({'status':'error','message':'user_exists'}),400
    u = User(email=email, name=name, role=RoleEnum.user)
    u.set_password(password)
    db.session.add(u); db.session.commit()
    return jsonify({'status':'ok','user':{'id':u.id,'email':u.email,'name':u.name}})

@bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email'); password = data.get('password')
    u = User.query.filter_by(email=email).first()
    if not u or not u.check_password(password):
        return jsonify({'status':'error','message':'invalid_credentials'}),401
    token = create_access_token(identity={'id':u.id,'role':u.role.value,'email':u.email})
    return jsonify({'status':'ok','token':token,'user':{'id':u.id,'email':u.email,'role':u.role.value,'name':u.name}})

# --- Helpers ---
def check_role(required_roles):
    identity = get_jwt_identity()
    if not identity or identity.get('role') not in required_roles:
        return False
    return True

# Create RRPP (admin only)
@bp.route('/api/rrpp', methods=['POST'])
@jwt_required()
def create_rrpp():
    if not check_role(['admin']):
        return jsonify({'status':'error','message':'forbidden'}),403
    data = request.get_json() or {}
    email = data.get('email'); name = data.get('name','RRPP'); password = data.get('password','RrppPass123!')
    if User.query.filter_by(email=email).first():
        return jsonify({'status':'error','message':'exists'}),400
    u = User(email=email, name=name, role=RoleEnum.rrpp)
    u.set_password(password)
    db.session.add(u); db.session.commit()
    return jsonify({'status':'ok','rrpp':{'id':u.id,'email':u.email}})

# List events
@bp.route('/api/events', methods=['GET'])
def list_events():
    evs = Event.query.all()
    out = []
    for e in evs:
        out.append({'id':e.id,'title':e.title,'date':e.date.isoformat(),'capacity':e.capacity,'zones':e.zones})
    return jsonify({'status':'ok','events':out})

# Create event (admin)
@bp.route('/api/events', methods=['POST'])
@jwt_required()
def create_event():
    if not check_role(['admin']):
        return jsonify({'status':'error','message':'forbidden'}),403
    data = request.get_json() or {}
    title = data.get('title'); date = data.get('date'); capacity = int(data.get('capacity',0)); zones = data.get('zones',{})
    if not title or not date:
        return jsonify({'status':'error','message':'missing'}),400
    ev = Event(title=title, date=datetime.fromisoformat(date), capacity=capacity, zones=zones)
    db.session.add(ev); db.session.commit()
    return jsonify({'status':'ok','event':{'id':ev.id,'title':ev.title}})

# Buy ticket (nominative)
@bp.route('/api/buy', methods=['POST'])
@jwt_required()
def buy_ticket():
    data = request.get_json() or {}
    event_id = data.get('event_id'); zone = data.get('zone'); buyer_name = data.get('buyer_name'); buyer_email = data.get('buyer_email')
    ev = Event.query.filter_by(id=event_id).first()
    if not ev:
        return jsonify({'status':'error','message':'event_not_found'}),404
    sold = Ticket.query.filter_by(event_id=ev.id, zone=zone).count()
    cap = ev.zones.get(zone,0)
    if sold >= cap:
        return jsonify({'status':'error','message':'sold_out_zone'}),400
    t = Ticket(event_id=ev.id, zone=zone, owner_name=buyer_name, owner_email=buyer_email, nominative=True)
    db.session.add(t); db.session.commit()
    return jsonify({'status':'ok','ticket':{'id':t.id,'zone':t.zone,'owner':t.owner_name}})

# My tickets
@bp.route('/api/mytickets', methods=['GET'])
@jwt_required()
def my_tickets():
    identity = get_jwt_identity()
    u = User.query.get(identity.get('id'))
    if not u:
        return jsonify({'status':'error','message':'unknown_user'}),404
    ts = Ticket.query.filter((Ticket.owner_email==u.email)|(Ticket.owner_name==u.name)).all()
    out = []
    for t in ts:
        out.append({'id':t.id,'zone':t.zone,'used':t.used,'event_id':t.event_id})
    return jsonify({'status':'ok','tickets':out})

# Scan ticket
@bp.route('/api/scan', methods=['POST'])
@jwt_required()
def scan_ticket():
    identity = get_jwt_identity()
    if identity.get('role') not in ['scanner','admin','manager']:
        return jsonify({'status':'error','message':'forbidden'}),403
    data = request.get_json() or {}
    ticket_id = data.get('ticket_id')
    t = Ticket.query.filter_by(id=ticket_id).first()
    if not t:
        return jsonify({'status':'error','message':'ticket_not_found'}),404
    if t.used:
        return jsonify({'status':'error','message':'already_used'}),400
    t.used = True
    db.session.commit()
    return jsonify({'status':'ok','ticket':{'id':t.id,'used':t.used}})

# Stats (admin)
@bp.route('/api/stats', methods=['GET'])
@jwt_required()
def stats():
    if not check_role(['admin']):
        return jsonify({'status':'error','message':'forbidden'}),403
    ev = Event.query.first()
    if not ev:
        return jsonify({'status':'error','message':'no_event'}),404
    sold = Ticket.query.filter_by(event_id=ev.id).count()
    used = Ticket.query.filter_by(event_id=ev.id, used=True).count()
    zones = {}
    for z,v in ev.zones.items():
        zones[z] = Ticket.query.filter_by(event_id=ev.id, zone=z).count()
    return jsonify({'status':'ok','stats':{'sold':sold,'used':used,'capacity':ev.capacity,'zones':zones}})
