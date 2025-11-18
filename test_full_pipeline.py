"""
test_full_pipeline.py
전체 파이프라인 테스트: 검색 엔진 + QA 시스템

실제 FAISS 인덱스를 로드하고 검색 → 답변 생성까지 전체 파이프라인 테스트
"""

import os
import json
from dotenv import load_dotenv
from src.s5_embedding_manager import EmbeddingManager
from src.s6_search_engine import SearchEngine
from src.s7_qa_system_light import QASystem

# .env 파일 로드
load_dotenv()

# OpenAI API 키
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def load_vector_store(institution: str = "kb"):
    """
    벡터 스토어 로드
    
    Args:
        institution: 기관명 (hd, kb, khi)
    
    Returns:
        (faiss_index, metadata, chunks)
    """
    print(f"\n📂 {institution.upper()} 벡터 스토어 로드 중...")
    
    # 경로 설정
    vector_store_dir = f"data/vector_store/{institution}"
    processed_dir = f"data/processed/{institution}"
    
    index_path = os.path.join(vector_store_dir, "faiss_index.bin")
    metadata_path = os.path.join(vector_store_dir, "metadata.json")
    chunks_path = os.path.join(processed_dir, f"{institution}_chunks.json")
    
    # EmbeddingManager 초기화
    embedding_manager = EmbeddingManager(
        openai_api_key=OPENAI_API_KEY,
        model="text-embedding-3-large"
    )
    
    # FAISS 인덱스 로드
    faiss_index = embedding_manager.load_index(index_path)
    if not faiss_index:
        raise FileNotFoundError(f"FAISS 인덱스를 찾을 수 없습니다: {index_path}")
    
    # 메타데이터 로드
    metadata = embedding_manager.load_metadata(metadata_path)
    if not metadata:
        raise FileNotFoundError(f"메타데이터를 찾을 수 없습니다: {metadata_path}")
    
    # 청크 로드 (BM25용)
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"✓ 청크 로드: {len(chunks)}개")
    
    return faiss_index, metadata, chunks, embedding_manager


def test_single_institution(institution: str = "kb"):
    """단일 기관 테스트"""
    print("\n" + "="*80)
    print(f"🚀 {institution.upper()} 전체 파이프라인 테스트")
    print("="*80)
    
    # 1. 벡터 스토어 로드
    faiss_index, metadata, chunks, embedding_manager = load_vector_store(institution)
    
    # 2. 검색 엔진 초기화
    print("\n🔍 검색 엔진 초기화 중...")
    search_engine = SearchEngine(
        faiss_index=faiss_index,
        metadata=metadata,
        chunks=chunks,
        embedding_manager=embedding_manager
    )
    
    # 3. QA 시스템 초기화
    print("\n🤖 QA 시스템 초기화 중...")
    qa_system = QASystem(
        openai_api_key=OPENAI_API_KEY,
        model="gpt-4o"
    )
    
    # 4. 질문 답변 테스트
    query = "2024년 서울 아파트 가격 변동률은?"
    
    print("\n" + "="*80)
    print(f"❓ 질문: {query}")
    print("="*80)
    
    # 검색 수행
    print("\n🔍 하이브리드 검색 수행 중...")
    search_results = search_engine.hybrid_search(query, top_k=5)
    
    print(f"✓ 검색 완료: {len(search_results)}개 결과")
    for i, result in enumerate(search_results, 1):
        print(f"  {i}. [{result['metadata'].get('institution', 'unknown')}] "
              f"RRF Score: {result.get('rrf_score', 0):.4f}")
    
    # 답변 생성
    answer = qa_system.answer_question(
        query=query,
        search_results=search_results,
        rewrite=True
    )
    
    print("\n✅ 전체 파이프라인 테스트 완료!")
    return answer


def test_multi_institution():
    """여러 기관 통합 검색 테스트"""
    print("\n" + "="*80)
    print("🚀 다중 기관 통합 검색 테스트")
    print("="*80)
    
    institutions = ["hd", "kb", "khi"]
    all_results = []
    
    # QA 시스템 초기화
    qa_system = QASystem(
        openai_api_key=OPENAI_API_KEY,
        model="gpt-4o"
    )
    
    query = "2024년 부동산 시장 전망은?"
    
    # 각 기관별로 검색
    for institution in institutions:
        try:
            print(f"\n📂 {institution.upper()} 검색 중...")
            faiss_index, metadata, chunks, embedding_manager = load_vector_store(institution)
            
            search_engine = SearchEngine(
                faiss_index=faiss_index,
                metadata=metadata,
                chunks=chunks,
                embedding_manager=embedding_manager
            )
            
            results = search_engine.hybrid_search(query, top_k=3)
            all_results.extend(results)
            print(f"✓ {institution.upper()}: {len(results)}개 결과")
            
        except Exception as e:
            print(f"⚠ {institution.upper()} 검색 실패: {e}")
            continue
    
    # 통합 결과로 답변 생성
    if all_results:
        print(f"\n📊 총 {len(all_results)}개 결과로 답변 생성")
        answer = qa_system.answer_question(
            query=query,
            search_results=all_results,
            rewrite=True
        )
        print("\n✅ 다중 기관 통합 검색 완료!")
        return answer
    else:
        print("⚠ 검색 결과가 없습니다.")
        return None


def test_search_types():
    """검색 타입별 비교 테스트"""
    print("\n" + "="*80)
    print("🔍 검색 타입별 성능 비교")
    print("="*80)
    
    # 벡터 스토어 로드
    faiss_index, metadata, chunks, embedding_manager = load_vector_store("kb")
    
    # 검색 엔진 초기화
    search_engine = SearchEngine(
        faiss_index=faiss_index,
        metadata=metadata,
        chunks=chunks,
        embedding_manager=embedding_manager
    )
    
    # QA 시스템 초기화
    qa_system = QASystem(
        openai_api_key=OPENAI_API_KEY,
        model="gpt-4o"
    )
    
    query = "강남구 아파트 가격"
    
    # 1. 벡터 검색만
    print("\n1️⃣ 벡터 검색 (의미 기반)")
    vector_results = search_engine.vector_search(query, top_k=5)
    print(f"결과: {len(vector_results)}개")
    
    # 2. 키워드 검색만
    print("\n2️⃣ 키워드 검색 (BM25)")
    keyword_results = search_engine.keyword_search(query, top_k=5)
    print(f"결과: {len(keyword_results)}개")
    
    # 3. 하이브리드 검색
    print("\n3️⃣ 하이브리드 검색 (RRF)")
    hybrid_results = search_engine.hybrid_search(query, top_k=5)
    print(f"결과: {len(hybrid_results)}개")
    
    # 하이브리드로 답변 생성
    print("\n💡 하이브리드 결과로 답변 생성:")
    answer = qa_system.answer_question(
        query=query,
        search_results=hybrid_results,
        rewrite=False
    )
    
    print("\n✅ 검색 타입 비교 완료!")
    return answer


def interactive_mode(institution: str = "kb"):
    """대화형 모드"""
    print("\n" + "="*80)
    print(f"💬 대화형 모드 ({institution.upper()} 리포트)")
    print("="*80)
    print("종료하려면 'exit' 또는 'quit'를 입력하세요.\n")
    
    # 초기화
    faiss_index, metadata, chunks, embedding_manager = load_vector_store(institution)
    
    search_engine = SearchEngine(
        faiss_index=faiss_index,
        metadata=metadata,
        chunks=chunks,
        embedding_manager=embedding_manager
    )
    
    qa_system = QASystem(
        openai_api_key=OPENAI_API_KEY,
        model="gpt-4o"
    )
    
    # 대화 루프
    while True:
        try:
            query = input("\n질문: ").strip()
            
            if query.lower() in ['exit', 'quit', '종료']:
                print("\n👋 대화를 종료합니다.")
                break
            
            if not query:
                continue
            
            # 검색 + 답변
            search_results = search_engine.hybrid_search(query, top_k=5)
            answer = qa_system.answer_question(
                query=query,
                search_results=search_results,
                rewrite=True
            )
            
        except KeyboardInterrupt:
            print("\n\n👋 대화를 종료합니다.")
            break
        except Exception as e:
            print(f"\n⚠ 오류 발생: {e}")


if __name__ == "__main__":
    print("\n" + "🏠 " + "="*76)
    print("부동산 리포트 QA 시스템 - 전체 파이프라인 테스트")
    print("="*80)
    
    # API 키 확인
    if not OPENAI_API_KEY:
        print("⚠️  경고: .env 파일에 OPENAI_API_KEY를 설정하세요!")
        exit(1)
    
    print(f"✓ API 키 로드 완료")
    
    # 테스트 선택
    print("\n테스트 옵션:")
    print("1. 단일 기관 테스트 (KB)")
    print("2. 단일 기관 테스트 (HD)")
    print("3. 단일 기관 테스트 (KHI)")
    print("4. 다중 기관 통합 검색")
    print("5. 검색 타입 비교")
    print("6. 대화형 모드 (KB)")
    print("7. 대화형 모드 (HD)")
    print("8. 대화형 모드 (KHI)")
    
    choice = input("\n선택 (1-8): ").strip()
    
    try:
        if choice == "1":
            test_single_institution("kb")
        elif choice == "2":
            test_single_institution("hd")
        elif choice == "3":
            test_single_institution("khi")
        elif choice == "4":
            test_multi_institution()
        elif choice == "5":
            test_search_types()
        elif choice == "6":
            interactive_mode("kb")
        elif choice == "7":
            interactive_mode("hd")
        elif choice == "8":
            interactive_mode("khi")
        else:
            print("잘못된 선택입니다. KB 테스트를 실행합니다.")
            test_single_institution("kb")
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다: {e}")
        print("\n필요한 파일:")
        print("  - data/vector_store/{institution}/faiss_index.bin")
        print("  - data/vector_store/{institution}/metadata.json")
        print("  - data/processed/{institution}/{institution}_chunks.json")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("🎉 테스트 완료!")
    print("="*80)