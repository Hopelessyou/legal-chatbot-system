"""
채팅 관련 API 라우터
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, model_validator
from typing import Optional, Dict, Any, List
from pathlib import Path
import os
import uuid
import mimetypes
from src.utils.response import success_response, error_response
from src.utils.exceptions import SessionNotFoundError, InvalidInputError
from src.utils.constants import SessionStatus
from src.db.connection import db_manager
from src.db.models.chat_session import ChatSession
from src.db.models.chat_file import ChatFile
from src.db.models.case_summary import CaseSummary
from src.db.models.case_master import CaseMaster
from src.services.session_manager import (
    SessionManager,
    validate_session_id,
    load_session_state,
    save_session_state
)
from src.langgraph.graph import run_graph_step
from src.langgraph.state import create_initial_context, StateContext
from src.api.auth import verify_api_key
from config.settings import settings
from src.utils.logger import get_logger
from fastapi import Request

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# 파일 업로드 보안 설정
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".txt", ".xlsx", ".xls"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel"
}


# Request/Response 모델
class ChatStartRequest(BaseModel):
    channel: str = "web"
    user_meta: Optional[Dict[str, Any]] = None
    # 편의를 위해 user_id와 device를 직접 받을 수 있도록 추가
    user_id: Optional[str] = None
    device: Optional[str] = None
    
    @model_validator(mode='after')
    def build_user_meta(self):
        """user_id나 device가 직접 제공된 경우 user_meta에 포함"""
        if (self.user_id or self.device) and not self.user_meta:
            self.user_meta = {}
            if self.user_id:
                self.user_meta["user_id"] = self.user_id
            if self.device:
                self.user_meta["device"] = self.device
        return self


class ChatMessageRequest(BaseModel):
    session_id: str
    user_message: str


class ChatEndRequest(BaseModel):
    session_id: str


# Response 모델
class ChatStartResponse(BaseModel):
    session_id: str
    state: str
    bot_message: str
    expected_input: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    session_id: str
    current_state: str
    completion_rate: int
    bot_message: str
    expected_input: Optional[Dict[str, Any]] = None


@router.post("/start")
async def start_chat(request: ChatStartRequest, _: str = Depends(verify_api_key)):
    """상담 세션 시작"""
    try:
        # 세션 생성
        session_id = SessionManager.create_session(
            channel=request.channel,
            user_identifier=request.user_meta.get("user_id") if request.user_meta else None
        )
        
        # 초기 Context 생성
        context = create_initial_context(session_id)
        context["channel"] = request.channel
        
        # INIT Node 실행
        result = run_graph_step(context)
        
        # 상태 저장 (다음 메시지에서 올바른 State로 시작하기 위해)
        save_session_state(session_id, result)
        
        return success_response({
            "session_id": session_id,
            "state": result.get("current_state", "INIT"),
            "bot_message": result.get("bot_message", ""),
            "expected_input": result.get("expected_input")
        })
    
    except Exception as e:
        logger.error(f"상담 세션 시작 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")


@router.post("/message")
async def process_message(request: ChatMessageRequest, _: str = Depends(verify_api_key)):
    """사용자 메시지 처리"""
    import sys
    import os
    # 강제로 stderr에 출력 (uvicorn이 캡처해도 보이도록)
    os.write(2, b"\n" + b"="*70 + b"\n")
    os.write(2, "[API] /chat/message 요청 수신!!!\n".encode('utf-8'))
    os.write(2, f"세션 ID: {request.session_id}\n".encode('utf-8'))
    os.write(2, f"사용자 메시지: {request.user_message[:100]}...\n".encode('utf-8'))
    os.write(2, b"="*70 + b"\n\n")
    try:
        # 세션 ID 검증
        if not validate_session_id(request.session_id):
            raise InvalidInputError("유효하지 않은 세션 ID 형식입니다.", "session_id")
        
        # 세션 상태 로드
        state = load_session_state(request.session_id)
        if not state:
            raise SessionNotFoundError(request.session_id)
        
        # 사용자 입력 업데이트
        state["last_user_input"] = request.user_message
        
        # 디버깅 로그 (강제 출력)
        import sys
        sys.stderr.write("\n" + "="*70 + "\n")
        sys.stderr.write(f"📨 [API] 메시지 수신\n")
        sys.stderr.write(f"📌 세션 ID: {request.session_id}\n")
        sys.stderr.write(f"📝 사용자 메시지: {request.user_message[:100]}...\n")
        sys.stderr.write(f"🔄 현재 State: {state.get('current_state')}\n")
        sys.stderr.write("="*70 + "\n")
        sys.stderr.flush()
        logger.info("="*70)
        logger.info(f"📨 [API] 메시지 수신")
        logger.info(f"📌 세션 ID: {request.session_id}")
        logger.info(f"📝 사용자 메시지: {request.user_message[:100]}...")
        logger.info(f"🔄 현재 State: {state.get('current_state')}")
        logger.info("="*70)
        logger.info(f"메시지 처리 시작: session_id={request.session_id}, current_state={state.get('current_state')}, user_message={request.user_message[:50]}...")
        
        # LangGraph 1 step 실행
        sys.stderr.write(f"▶️  LangGraph 실행 시작...\n")
        sys.stderr.flush()
        logger.info(f"▶️  LangGraph 실행 시작...")
        result = run_graph_step(state)
        sys.stderr.write(f"✅ LangGraph 실행 완료\n")
        sys.stderr.flush()
        logger.info(f"✅ LangGraph 실행 완료")
        
        bot_message = result.get('bot_message') or ''
        bot_message_preview = bot_message[:50] if bot_message else '(메시지 없음)'
        
        # Q-A 매칭 방식 디버깅 정보 로깅
        conversation_history = result.get("conversation_history", [])
        skipped_fields = result.get("skipped_fields", [])
        initial_analysis = result.get("initial_analysis")
        
        logger.info(
            f"메시지 처리 완료: new_state={result.get('current_state')}, "
            f"bot_message={bot_message_preview}..., "
            f"conversation_history={len(conversation_history)}개, "
            f"skipped_fields={skipped_fields}"
        )
        
        # 상태 저장
        save_session_state(request.session_id, result)
        
        # 응답 데이터 구성 (Q-A 매칭 방식 디버깅 정보 포함)
        response_data = {
            "session_id": request.session_id,
            "current_state": result.get("current_state", ""),
            "completion_rate": result.get("completion_rate", 0),
            "bot_message": result.get("bot_message", ""),
            "expected_input": result.get("expected_input"),
            # Q-A 매칭 방식 디버깅 정보
            "conversation_history": result.get("conversation_history", []),
            "skipped_fields": result.get("skipped_fields", []),
            "initial_analysis": result.get("initial_analysis"),
            "current_question": result.get("current_question")
        }
        
        logger.debug(f"응답 데이터: bot_message={response_data['bot_message'][:100] if response_data['bot_message'] else '(없음)'}, skipped_fields={response_data['skipped_fields']}, conversation_history={len(response_data['conversation_history'])}개")
        
        return success_response(response_data)
    
    except SessionNotFoundError as e:
        logger.error(f"메시지 처리 실패 (세션 없음): {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        logger.error(f"메시지 처리 실패 (잘못된 입력): {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"메시지 처리 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")


@router.post("/end")
async def end_chat(request: ChatEndRequest, _: str = Depends(verify_api_key)):
    """상담 종료"""
    try:
        # 세션 검증
        session = SessionManager.get_session(request.session_id)
        if not session:
            raise SessionNotFoundError(request.session_id)
        
        # 세션 상태 로드
        state = load_session_state(request.session_id)
        if not state:
            raise SessionNotFoundError(request.session_id)
        
        # SUMMARY → COMPLETED 실행 (아직 SUMMARY가 아닌 경우)
        # 하나의 DB 세션으로 통합하여 트랜잭션 일관성 확보
        with db_manager.get_db_session() as db_session:
            if state.get("current_state") != "COMPLETED":
                # SUMMARY Node 실행
                from src.langgraph.nodes.summary_node import summary_node
                state = summary_node(state)
                
                # COMPLETED Node 실행
                from src.langgraph.nodes.completed_node import completed_node
                state = completed_node(state)
                
                # 상태 저장 (같은 세션 사용)
                save_session_state(request.session_id, state, db_session=db_session)
            
            # 최종 결과 조회 (같은 세션 사용)
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == request.session_id
            ).first()
            
            summary_data = {}
            if case:
                summary = db_session.query(CaseSummary).filter(
                    CaseSummary.case_id == case.case_id
                ).first()
                
                if summary:
                    summary_data = {
                        "summary_text": summary.summary_text,
                        "structured_data": summary.structured_json
                    }
            
            return success_response({
                "session_id": request.session_id,
                "final_state": "COMPLETED",
                "completion_rate": session.completion_rate,
                "summary": summary_data
            })
    
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_chat_status(session_id: str, _: str = Depends(verify_api_key)):
    """현재 상담 상태 조회"""
    try:
        with db_manager.get_db_session() as db_session:
            # 세션 조회
            session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                raise SessionNotFoundError(session_id)
            
            # 누락 필드 조회
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            filled_fields = []
            missing_fields = []
            
            if case:
                from src.db.models.case_missing_field import CaseMissingField
                missing_field_records = db_session.query(CaseMissingField).filter(
                    CaseMissingField.case_id == case.case_id,
                    CaseMissingField.resolved == False
                ).all()
                
                missing_fields = [mf.field_key for mf in missing_field_records]
                
                # 채워진 필드 계산 (간단화)
                filled_fields = ["incident_date", "counterparty", "amount", "evidence"]
                filled_fields = [f for f in filled_fields if f not in missing_fields]
            
            return success_response({
                "session_id": session_id,
                "current_state": session.current_state,  # state -> current_state로 변경
                "status": session.status,  # status 추가
                "completion_rate": session.completion_rate,
                "filled_fields": filled_fields,
                "missing_fields": missing_fields
            })
    
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detail")
async def get_session_detail(session_id: str, _: str = Depends(verify_api_key)):
    """세션 상세 정보 조회 (관리자용)"""
    try:
        if not validate_session_id(session_id):
            raise InvalidInputError("유효하지 않은 세션 ID 형식입니다.", "session_id")
        
        with db_manager.get_db_session() as db_session:
            # 세션 조회
            session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                raise SessionNotFoundError(session_id)
            
            # Case 정보
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            case_info = None
            if case:
                # Party 정보
                from src.db.models.case_party import CaseParty
                parties = db_session.query(CaseParty).filter(
                    CaseParty.case_id == case.case_id
                ).all()
                
                # Fact 정보
                from src.db.models.case_fact import CaseFact
                facts = db_session.query(CaseFact).filter(
                    CaseFact.case_id == case.case_id
                ).all()
                
                # Evidence 정보
                from src.db.models.case_evidence import CaseEvidence
                evidences = db_session.query(CaseEvidence).filter(
                    CaseEvidence.case_id == case.case_id
                ).all()
                
                # Summary 정보
                summary = db_session.query(CaseSummary).filter(
                    CaseSummary.case_id == case.case_id
                ).first()
                
                # 각 데이터를 안전하게 처리
                parties_list = []
                try:
                    parties_list = [{
                        "party_type": p.party_type,
                        "name": p.name,
                        "age": p.age,
                        "gender": p.gender,
                        "relationship": p.relationship
                    } for p in parties]
                except Exception as e:
                    logger.warning(f"당사자 정보 조회 중 오류: {str(e)}")
                
                facts_list = []
                try:
                    facts_list = [{
                        "fact_type": f.fact_type,
                        "content": f.content,
                        "date": f.date.isoformat() if f.date else None
                    } for f in facts]
                except Exception as e:
                    logger.warning(f"사실관계 정보 조회 중 오류: {str(e)}")
                
                evidences_list = []
                try:
                    evidences_list = [{
                        "evidence_type": e.evidence_type,
                        "description": e.description,
                        "available": e.available
                    } for e in evidences]
                except Exception as e:
                    logger.warning(f"증거 정보 조회 중 오류: {str(e)}")
                
                summary_info = None
                try:
                    if summary:
                        summary_info = {
                            "summary_text": summary.summary_text if summary else None,
                            "structured_json": summary.structured_json if summary else None
                        }
                except Exception as e:
                    logger.warning(f"요약 정보 조회 중 오류: {str(e)}")
                
                case_info = {
                    "case_id": case.case_id,
                    "main_case_type": case.main_case_type,
                    "sub_case_type": case.sub_case_type,
                    "case_stage": case.case_stage,
                    "urgency_level": case.urgency_level,
                    "estimated_value": case.estimated_value,
                    "parties": parties_list,
                    "facts": facts_list,
                    "evidences": evidences_list,
                    "summary": summary_info
                }
            
            # 파일 목록 (ChatFile 테이블이 없을 수 있으므로 try-except 처리)
            file_list = []
            try:
                files = db_session.query(ChatFile).filter(
                    ChatFile.session_id == session_id
                ).order_by(ChatFile.uploaded_at.desc()).all()
                
                file_list = [{
                    "id": f.id,
                    "file_name": f.file_name,
                    "file_size": f.file_size,
                    "file_type": f.file_type,
                    "file_extension": f.file_extension,
                    "description": f.description,
                    "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None
                } for f in files]
            except Exception as e:
                logger.warning(f"파일 목록 조회 중 오류 (테이블이 없을 수 있음): {str(e)}")
                file_list = []
            
            # conversation_history 가져오기 (DB에서 직접)
            conversation_history = []
            try:
                if session.conversation_history:
                    conversation_history = session.conversation_history
                    logger.info(f"conversation_history 로드 완료: {session_id}, {len(conversation_history)}개 Q-A 쌍")
                else:
                    logger.debug(f"conversation_history 없음: {session_id}")
            except Exception as e:
                logger.warning(f"conversation_history 조회 중 오류: {str(e)}")
                conversation_history = []
            
            return success_response({
                "session": {
                    "session_id": session.session_id,
                    "channel": session.channel,
                    "status": session.status,
                    "current_state": session.current_state,
                    "completion_rate": session.completion_rate,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                },
                "case": case_info,
                "files": file_list,
                "conversation_history": conversation_history
            })
    
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"세션 상세 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"세션 상세 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/result")
async def get_chat_result(session_id: str, _: str = Depends(verify_api_key)):
    """최종 상담 결과 조회"""
    try:
        with db_manager.get_db_session() as db_session:
            # 세션 조회
            session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                raise SessionNotFoundError(session_id)
            
            if session.status != SessionStatus.COMPLETED.value:
                raise HTTPException(
                    status_code=400,
                    detail="상담이 아직 완료되지 않았습니다."
                )
            
            # case_summary 조회
            case = db_session.query(CaseMaster).filter(
                CaseMaster.session_id == session_id
            ).first()
            
            if not case:
                raise HTTPException(status_code=404, detail="사건 정보를 찾을 수 없습니다.")
            
            summary = db_session.query(CaseSummary).filter(
                CaseSummary.case_id == case.case_id
            ).first()
            
            if not summary:
                raise HTTPException(status_code=404, detail="요약 정보를 찾을 수 없습니다.")
            
            return success_response({
                "case_summary_text": summary.summary_text,
                "structured_data": summary.structured_json or {},
                "completion_rate": session.completion_rate
            })
    
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(
    _: str = Depends(verify_api_key),
    session_id: str = Form(...),
    description: Optional[str] = Form(None),
    files: List[UploadFile] = File(...)
):
    """파일 업로드 및 DB 저장"""
    try:
        # 세션 검증
        if not validate_session_id(session_id):
            raise InvalidInputError("유효하지 않은 세션 ID 형식입니다.", "session_id")
        
        with db_manager.get_db_session() as db_session:
            session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                raise SessionNotFoundError(session_id)
        
        # 업로드 디렉토리 생성
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 세션별 디렉토리 생성
        session_upload_dir = upload_dir / session_id
        session_upload_dir.mkdir(parents=True, exist_ok=True)
        
        max_file_size = settings.max_file_size_mb * 1024 * 1024  # MB to bytes
        uploaded_files = []
        
        # 모든 파일을 하나의 트랜잭션으로 저장
        with db_manager.get_db_session() as db_session:
            for file in files:
                # 파일명 정규화 (경로 탐색 공격 방지)
                safe_filename = Path(file.filename).name  # 경로 제거
                if ".." in safe_filename or "/" in safe_filename or "\\" in safe_filename:
                    raise HTTPException(
                        status_code=400,
                        detail=f"파일명에 경로 문자가 포함되어 있습니다: {file.filename}"
                    )
                
                # 파일 크기 검증
                file_content = await file.read()
                file_size = len(file_content)
                
                if file_size > max_file_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"파일 '{safe_filename}'이 너무 큽니다. (최대 {settings.max_file_size_mb}MB)"
                    )
                
                if file_size == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"파일 '{safe_filename}'이 비어있습니다."
                    )
                
                # 파일 확장자 검증
                file_ext = Path(safe_filename).suffix.lower()
                if file_ext not in ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"허용되지 않은 파일 형식입니다: {file_ext}. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}"
                    )
                
                # MIME 타입 검증
                mime_type, _ = mimetypes.guess_type(safe_filename)
                if mime_type and mime_type not in ALLOWED_MIME_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"허용되지 않은 MIME 타입입니다: {mime_type}"
                    )
                
                # 고유한 파일명 생성 (중복 방지)
                unique_filename = f"{uuid.uuid4().hex}{file_ext}"
                file_path = session_upload_dir / unique_filename
                
                # 경로 검증 (절대 경로로 변환 후 upload_dir 내부인지 확인)
                upload_dir_resolved = upload_dir.resolve()
                file_path_resolved = file_path.resolve()
                if not str(file_path_resolved).startswith(str(upload_dir_resolved)):
                    raise HTTPException(
                        status_code=403,
                        detail="접근할 수 없는 파일 경로입니다."
                    )
                
                # 파일 저장
                with open(file_path, "wb") as f:
                    f.write(file_content)
                
                # DB에 파일 정보 저장 (트랜잭션 내에서)
                chat_file = ChatFile(
                    session_id=session_id,
                    file_name=safe_filename,
                    file_path=str(file_path.relative_to(upload_dir)),  # 상대 경로 저장
                    file_size=file_size,
                    file_type=mime_type or "application/octet-stream",
                    file_extension=file_ext,
                    description=description
                )
                db_session.add(chat_file)
                logger.info(f"파일 업로드 완료: session_id={session_id}, file={safe_filename}, size={file_size}")
            
            # 모든 파일 저장 후 한 번에 커밋
            db_session.commit()
            
            # 업로드된 파일 정보 조회
            for chat_file in db_session.query(ChatFile).filter(
                ChatFile.session_id == session_id
            ).order_by(ChatFile.uploaded_at.desc()).limit(len(files)).all():
                uploaded_files.append({
                    "id": chat_file.id,
                    "file_name": chat_file.file_name,
                    "file_size": chat_file.file_size,
                    "file_type": chat_file.file_type,
                    "uploaded_at": chat_file.uploaded_at.isoformat() if chat_file.uploaded_at else None
                })
        
        return success_response({
            "session_id": session_id,
            "uploaded_count": len(uploaded_files),
            "files": uploaded_files
        })
    
    except SessionNotFoundError as e:
        logger.error(f"파일 업로드 실패 (세션 없음): {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        logger.error(f"파일 업로드 실패 (잘못된 입력): {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}")


@router.get("/list")
async def list_sessions(
    limit: int = 50,
    status: Optional[str] = None,
    offset: int = 0,
    _: str = Depends(verify_api_key)
):
    """세션 목록 조회 (관리자용)"""
    try:
        with db_manager.get_db_session() as db_session:
            query = db_session.query(ChatSession)
            
            # 상태 필터
            if status:
                query = query.filter(ChatSession.status == status)
            
            # 정렬 및 제한
            sessions = query.order_by(
                ChatSession.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            session_list = []
            for session in sessions:
                # Case 정보 조회
                case = db_session.query(CaseMaster).filter(
                    CaseMaster.session_id == session.session_id
                ).first()
                
                case_type = None
                if case:
                    case_type = case.main_case_type or case.sub_case_type
                
                # Summary 존재 여부
                has_summary = False
                if case:
                    summary = db_session.query(CaseSummary).filter(
                        CaseSummary.case_id == case.case_id
                    ).first()
                    has_summary = summary is not None
                
                # 파일 존재 여부
                has_files = False
                file_count = 0
                try:
                    files = db_session.query(ChatFile).filter(
                        ChatFile.session_id == session.session_id
                    ).all()
                    has_files = len(files) > 0
                    file_count = len(files)
                except Exception as e:
                    logger.warning(f"파일 개수 조회 중 오류 (테이블이 없을 수 있음): {str(e)}")
                
                session_list.append({
                    "session_id": session.session_id,
                    "channel": session.channel,
                    "status": session.status,
                    "current_state": session.current_state,
                    "completion_rate": session.completion_rate,
                    "case_type": case_type,
                    "has_summary": has_summary,
                    "has_files": has_files,
                    "file_count": file_count,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                })
            
            # 전체 개수
            total_count = query.count()
            
            return success_response({
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "sessions": session_list
            })
    
    except Exception as e:
        logger.error(f"세션 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"세션 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/files")
async def get_session_files(session_id: str, _: str = Depends(verify_api_key)):
    """세션에 첨부된 파일 목록 조회"""
    try:
        # 세션 검증
        if not validate_session_id(session_id):
            raise InvalidInputError("유효하지 않은 세션 ID 형식입니다.", "session_id")
        
        with db_manager.get_db_session() as db_session:
            # 세션 존재 확인
            session = db_session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if not session:
                raise SessionNotFoundError(session_id)
            
            # 파일 목록 조회
            files = db_session.query(ChatFile).filter(
                ChatFile.session_id == session_id
            ).order_by(ChatFile.uploaded_at.desc()).all()
            
            file_list = [{
                "id": f.id,
                "file_name": f.file_name,
                "file_size": f.file_size,
                "file_type": f.file_type,
                "file_extension": f.file_extension,
                "description": f.description,
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None
            } for f in files]
            
            return success_response({
                "session_id": session_id,
                "file_count": len(file_list),
                "files": file_list
            })
    
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/file/{file_id}/download")
async def download_file(file_id: int, _: str = Depends(verify_api_key)):
    """파일 다운로드"""
    try:
        with db_manager.get_db_session() as db_session:
            # 파일 정보 조회
            chat_file = db_session.query(ChatFile).filter(
                ChatFile.id == file_id
            ).first()
            
            if not chat_file:
                raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
            
            # 파일 경로 구성 및 검증
            upload_dir = Path(settings.upload_dir).resolve()
            file_path = (upload_dir / chat_file.file_path).resolve()
            
            # 경로 탐색 공격 방지 (upload_dir 외부 접근 차단)
            if not str(file_path).startswith(str(upload_dir)):
                raise HTTPException(
                    status_code=403,
                    detail="접근할 수 없는 파일 경로입니다."
                )
            
            # 파일 존재 확인
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="파일이 서버에 존재하지 않습니다.")
            
            # 파일 다운로드 응답
            return FileResponse(
                path=str(file_path),
                filename=chat_file.file_name,
                media_type=chat_file.file_type or "application/octet-stream"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 다운로드 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")

