from sqlalchemy import Column, String, DateTime, BigInteger, Text, Float
import datetime
import pytz
from bot.sql_helper import Base, Session, engine
from cacheout import Cache

# Beijing timezone for consistent time handling
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

cache = Cache()


def get_beijing_time():
    """Get current time in Beijing timezone"""
    return datetime.datetime.now(BEIJING_TZ)


class RequestRecord(Base):
    __tablename__ = 'request_records'
    download_id = Column(String(255), primary_key=True, autoincrement=False)
    tg = Column(BigInteger, nullable=False)  # Telegram user ID for tracking demand requests
    request_name = Column(String(255), nullable=False)
    cost = Column(String(255), nullable=False)
    detail = Column(Text, nullable=False)
    left_time = Column(String(255))
    download_state= Column(String(50), default='pending')  # pending, downloading, completed, failed
    transfer_state = Column(String(50))  # success, failed
    progress = Column(Float, default=0)
    create_at = Column(DateTime, default=get_beijing_time)  # Store demands in Beijing time (UTC+8)
    update_at = Column(DateTime, default=get_beijing_time,
                      onupdate=get_beijing_time)  # Update timestamps in Beijing time


RequestRecord.__table__.create(bind=engine, checkfirst=True)


def sql_add_request_record(tg: int, download_id: str, request_name: str, detail: str, cost: str):
    with Session() as session:
        try:
            request_record = RequestRecord(
                tg=tg, download_id=download_id, request_name=request_name, detail=detail, cost=cost, left_time='一万年吧')
            session.add(request_record)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False


def sql_get_all_request_records(page: int = 1, limit: int = 20):
    """获取所有请求记录，支持分页"""
    with Session() as session:
        total_count = session.query(RequestRecord).count()
        request_records = session.query(RequestRecord).order_by(
            RequestRecord.create_at.desc()).limit(limit + 1).offset((page - 1) * limit).all()
        
        if len(request_records) == 0:
            return [], False, False, total_count
        
        if len(request_records) == limit + 1:
            has_next = True
            request_records = request_records[:-1]
        else:
            has_next = False
        
        has_prev = page > 1
        return request_records, has_prev, has_next, total_count


def sql_delete_request_record(download_id: str):
    """根据下载ID删除请求记录"""
    with Session() as session:
        try:
            record = session.query(RequestRecord).filter(
                RequestRecord.download_id == download_id).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            return False


def sql_get_request_records_by_state(download_state: str = None, transfer_state: str = None, page: int = 1, limit: int = 20):
    """根据状态获取请求记录"""
    with Session() as session:
        query = session.query(RequestRecord)
        
        if download_state:
            query = query.filter(RequestRecord.download_state == download_state)
        if transfer_state:
            query = query.filter(RequestRecord.transfer_state == transfer_state)
            
        total_count = query.count()
        request_records = query.order_by(RequestRecord.create_at.desc()).limit(limit + 1).offset((page - 1) * limit).all()
        
        if len(request_records) == 0:
            return [], False, False, total_count
        
        if len(request_records) == limit + 1:
            has_next = True
            request_records = request_records[:-1]
        else:
            has_next = False
        
        has_prev = page > 1
        return request_records, has_prev, has_next, total_count


def sql_get_request_record_by_tg(tg: int, page: int = 1, limit: int = 5):
    with Session() as session:
        request_record = session.query(RequestRecord).filter(
            RequestRecord.tg == tg).order_by(RequestRecord.create_at.desc()).limit(limit + 1).offset((page - 1) * limit).all()
        if len(request_record) == 0:
            return None, False, False
        if len(request_record) == limit + 1:
            has_next = True
            request_record = request_record[:-1]
        else:
            has_next = False
        if page > 1:
            has_prev = True
        else:
            has_prev = False
        return request_record, has_prev, has_next

def sql_get_request_record_by_download_id(download_id: str):
    with Session() as session:
        request_record = session.query(RequestRecord).filter(RequestRecord.download_id == download_id).first()
        return request_record

def sql_get_request_record_by_transfer_state(transfer_state: str = None):
    with Session() as session:
        request_record = session.query(RequestRecord).filter(RequestRecord.transfer_state == transfer_state).all()
        return request_record


def sql_update_request_status(download_id: str, download_state: str, transfer_state: str = None, progress: float = None, left_time: str = None):
    """更新下载状态"""
    with Session() as session:
        try:
            record = session.query(RequestRecord).filter(
                RequestRecord.download_id == download_id).first()
            if record:
                if download_state is not None:
                    record.download_state = download_state
                if transfer_state is not None:
                    record.transfer_state = transfer_state
                if progress is not None:
                    record.progress = progress
                if left_time is not None:
                    record.left_time = left_time
                session.commit()
                return True
        except Exception as e:
            session.rollback()
            return False


def sql_check_existing_request_by_title(movie_title: str):
    """检查影片是否已经被点播（任何用户）"""
    with Session() as session:
        try:
            # 清理输入以防止SQL注入
            clean_title = movie_title.replace('%', '\\%').replace('_', '\\_') if movie_title else ""
            if not clean_title:
                return None
                
            # 查找任何用户的相同影片请求，排除已完全失败的请求
            existing_request = session.query(RequestRecord).filter(
                RequestRecord.request_name.like(f"%{clean_title}%")
            ).filter(
                # 只排除同时满足下载失败和入库失败的请求
                ~((RequestRecord.download_state == 'failed') & 
                  ((RequestRecord.transfer_state == False) | (RequestRecord.transfer_state == None)))
            ).order_by(RequestRecord.create_at.desc()).first()
            
            return existing_request
        except Exception as e:
            return None
