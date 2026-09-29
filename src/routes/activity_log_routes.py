from datetime import datetime

from flask import Blueprint, request

from src import db
from src.models.activity_logs import ActivityLog
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    tenant_scope, current_business_id,
)
from src.utils.constants import MODULE_ACTIVITY_LOGS, ROLE_STAFF

bp = Blueprint('activity_logs', __name__, url_prefix='/api/activity-logs')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_activity_logs():
    """Audit trail (tenant + branch scoped) with the usual filters"""
    try:
        query = tenant_scope(ActivityLog, ActivityLog.query)

        if request.args.get('module'):
            query = query.filter(ActivityLog.module == request.args.get('module'))
        if request.args.get('action'):
            query = query.filter(ActivityLog.action == request.args.get('action'))
        if request.args.get('user_id'):
            query = query.filter(ActivityLog.user_id == request.args.get('user_id'))
        if request.args.get('from'):
            try:
                query = query.filter(ActivityLog.created_at >= datetime.strptime(request.args['from'][:10], '%Y-%m-%d'))
            except ValueError:
                return error_response('from must be in YYYY-MM-DD format', 400)
        if request.args.get('to'):
            try:
                to_date = datetime.strptime(request.args['to'][:10], '%Y-%m-%d')
                query = query.filter(ActivityLog.created_at <= to_date.replace(hour=23, minute=59, second=59))
            except ValueError:
                return error_response('to must be in YYYY-MM-DD format', 400)
        if request.args.get('search'):
            term = f"%{request.args.get('search')}%"
            query = query.filter(db.or_(
                ActivityLog.description.ilike(term),
                ActivityLog.user_name.ilike(term),
                ActivityLog.record_ref.ilike(term)
            ))

        limit = int(request.args.get('limit', 200))
        logs = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit).all()
        return success_response('Activity logs fetched successfully',
                                [entry.to_dict() for entry in logs], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)
