"""
s4_test_chunking.py
각 기관별 processed.json 파일을 청킹하여 저장

사용법:
    python s4_test_chunking.py
"""

import sys
from pathlib import Path
import json

# 프로젝트 루트 경로를 sys.path에 추가
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# src 폴더의 모듈 임포트
from s4_chunking_strategy import ChunkingStrategy


def chunk_single_institution(institution: str):
    """
    단일 기관의 processed.json을 청킹
    
    Args:
        institution: 기관 코드 (hd, kb, khi)
    """
    print(f"\n{'='*80}")
    print(f"📄 {institution.upper()} 청킹 시작")
    print(f"{'='*80}\n")
    
    # 입력 파일 경로
    input_file = project_root / "data" / "processed" / institution / f"{institution}_report_processed.json"
    
    # 파일 존재 확인
    if not input_file.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        return None
    
    # 청킹 전략 초기화
    chunker = ChunkingStrategy(
        chunk_size=800,
        overlap=100,
        model="gpt-4"
    )
    
    # JSON 파일 로드 및 청킹
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    institution_code = data.get("institution", institution)
    
    print(f"✓ JSON 로드 완료: {input_file}")
    print(f"✓ 기관: {institution_code.upper()}")
    
    # 텍스트 수집
    texts = data.get("texts", [])
    print(f"  - 텍스트: {len(texts)}개 페이지")
    
    # 표 수집
    tables = data.get("tables", [])
    print(f"  - 표: {len(tables)}개")
    
    # 이미지 수집
    images = data.get("images", [])
    print(f"  - 이미지: {len(images)}개")
    
    # 1. 텍스트 청킹
    print(f"\n1️⃣ 텍스트 청킹 중...")
    text_blocks = []
    for text_data in texts:
        # 각 페이지의 텍스트를 블록으로 변환
        text_blocks.append({
            "text": text_data.get("text", ""),
            "page_num": text_data.get("page_num", 0)
        })
    
    text_chunks = chunker.chunk_pages(text_blocks, institution_code)
    print(f"  ✓ {len(text_chunks)}개 텍스트 청크 생성")
    
    # 2. 표 청킹
    print(f"\n2️⃣ 표 청킹 중...")
    table_chunks = []
    for table_data in tables:
        table_chunk = chunker.make_table_to_chunk(table_data)
        table_chunks.append(table_chunk)
    print(f"  ✓ {len(table_chunks)}개 표 청크 생성")
    
    # 3. 이미지 청킹
    print(f"\n3️⃣ 이미지 청킹 중...")
    image_chunks = []
    for image_data in images:
        image_chunk = chunker.make_image_to_chunk(image_data)
        image_chunks.append(image_chunk)
    print(f"  ✓ {len(image_chunks)}개 이미지 청크 생성")
    
    # 4. 모든 청크 결합
    all_chunks = text_chunks + table_chunks + image_chunks
    
    # 5. 오버랩 적용
    print(f"\n4️⃣ 오버랩 적용 중...")
    final_chunks = chunker.apply_overlap(all_chunks)
    print(f"  ✓ 최종 {len(final_chunks)}개 청크 생성")
    
    # 6. 결과 저장
    output_dir = project_root / "data" / "processed" / institution
    output_file = output_dir / f"{institution}_chunks.json"
    
    chunker.save_chunks(final_chunks, str(output_file))
    
    print(f"\n{'='*80}")
    print(f"✅ {institution.upper()} 청킹 완료!")
    print(f"{'='*80}\n")
    
    return final_chunks


def main():
    """
    메인 함수: 모든 기관 청킹
    """
    institutions = ["hd", "kb", "khi"]
    
    print("\n" + "="*80)
    print("🚀 전체 기관 청킹 시작")
    print("="*80)
    
    results = {}
    
    for institution in institutions:
        try:
            chunks = chunk_single_institution(institution)
            if chunks:
                results[institution] = len(chunks)
        except Exception as e:
            print(f"\n❌ {institution.upper()} 청킹 실패: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 전체 요약
    print("\n" + "="*80)
    print("✅ 전체 청킹 완료!")
    print("="*80)
    
    for institution, count in results.items():
        print(f"  - {institution.upper()}: {count}개 청크")
        output_file = project_root / "data" / "processed" / institution / f"{institution}_chunks.json"
        print(f"    → {output_file}")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    # 사용 예시 1: 전체 청킹
    main()
    
    # 사용 예시 2: 특정 기관만 청킹
    # chunk_single_institution("hd")