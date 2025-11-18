"""
qa_system.py
[6단계 통합] LLM 통합 - 대화 전용 버전

검색 결과를 LLM에 전달하여 자연스러운 답변 생성
- 쿼리 리라이팅
- 컨텍스트 구성
- 프롬프트 관리
- LLM 호출 (텍스트 답변만)
"""

from openai import OpenAI
from typing import List, Dict, Optional


class QASystem:
    """Q&A 시스템 통합 클래스 (텍스트 대화 전용)"""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4o"):
        """
        QASystem 초기화
        
        Args:
            openai_api_key: OpenAI API 키
            model: 사용할 모델명
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.system_prompt = self._create_system_prompt()
        print(f"✓ QASystem 초기화 완료 (모델: {model})")
    
    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성 (대화 전용)"""
        return """당신은 KB금융지주 경영연구소의 부동산 전문 애널리스트입니다.
2024 KB 부동산 보고서를 기반으로 건설사 실무진에게 정확하고 실무적인 정보를 제공합니다.

답변 가이드라인:
1. 제공된 리포트 내용만을 기반으로 답변하세요.
2. 수치 데이터는 정확하게 인용하세요.
3. 각 문장이나 정보의 끝에 반드시 출처 번호를 [1], [2] 형태로 표시하세요.
4. 모르는 내용은 추측하지 말고 "리포트에 해당 정보가 없습니다"라고 답하세요.
5. 건설사 실무진이 이해하기 쉽게 구조화된 형태로 답변하세요.

출처 표기 규칙:
- 각 문장 뒤에 [1], [2] 형태로 출처 번호 표기
- 답변 끝에 반드시 출처 목록 작성

답변 형식 예시:
2024년 서울 아파트 매매가격은 2.0% 상승했습니다. [1]
강남구는 전 고점을 돌파했습니다. [2]

출처:
[1] kb_report_2024.pdf 표Ⅰ-2. 지역별 주택 매매가격 변동률 (12페이지)
[2] kb_report_2024.pdf 본문 (25페이지)
"""
    
    def rewrite_query(self, query: str) -> str:
        """
        쿼리를 검색에 최적화된 형태로 리라이팅
        
        Args:
            query: 원본 쿼리
        
        Returns:
            최적화된 쿼리
        """
        prompt = f"""당신은 부동산 리포트 검색 전문가입니다.
사용자 질문을 검색에 최적화된 형태로 다시 작성해주세요.

요구사항:
- 구어체를 문어체로 변환
- 키워드를 명확하게
- 관련 동의어 추가
- 간결하게 (1-2문장)

원래 질문: {query}

최적화된 질문:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 검색 쿼리 최적화 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            rewritten = response.choices[0].message.content.strip()
            print(f"\n🔄 쿼리 리라이팅:")
            print(f"  원본: {query}")
            print(f"  변환: {rewritten}")
            
            return rewritten
            
        except Exception as e:
            print(f"⚠ 쿼리 리라이팅 실패: {e}")
            return query
    
    def build_context(self, search_results: List[Dict], max_chunks: int = 5) -> str:
        """
        검색 결과를 구조화된 컨텍스트로 변환
        
        Args:
            search_results: 검색 결과 리스트
            max_chunks: 최대 청크 수
        
        Returns:
            구조화된 컨텍스트 문자열
        """
        if not search_results:
            return "관련 정보를 찾을 수 없습니다."
        
        top_results = search_results[:max_chunks]
        
        context_parts = ["다음은 2024 KB 부동산 리포트에서 검색된 관련 정보입니다:\n"]
        
        for i, result in enumerate(top_results, 1):
            metadata = result.get("metadata", {})
            content = result.get("content", "")
            
            # 기관 정보
            institution = metadata.get("institution", "unknown")
            institution_map = {
                "hd": "HD 현대 리포트",
                "kb": "KB 부동산 리포트",
                "khi": "KHI 주택금융 리포트"
            }
            source_name = institution_map.get(institution, f"{institution} 리포트")
            
            # 문서 타입
            doc_type_map = {
                "text": "본문",
                "table": "표",
                "image": "그래프/이미지"
            }
            doc_type = doc_type_map.get(metadata.get("doc_type"), "본문")
            page = metadata.get("page", "unknown")
            
            # 추가 정보 (있는 경우)
            extra_info = ""
            if metadata.get("table_id"):
                extra_info = f"\n표 ID: {metadata.get('table_id')}"
            elif metadata.get("image_path"):
                image_path = metadata.get('image_path')
                image_filename = image_path.split('\\')[-1] if '\\' in image_path else image_path.split('/')[-1]
                extra_info = f"\n이미지: {image_filename}"
            
            formatted = f"""[컨텍스트 {i}]
출처 기관: {source_name}
타입: {doc_type}
페이지: {page}페이지{extra_info}

내용:
{content}

출처: [{i}] {source_name} {doc_type} ({page}페이지)
"""
            context_parts.append(formatted)
            context_parts.append("─" * 80 + "\n")
        
        full_context = "\n".join(context_parts)
        
        print(f"\n📄 컨텍스트 구성 완료:")
        print(f"  - 총 청크 수: {len(top_results)}")
        print(f"  - 텍스트: {len([r for r in top_results if r.get('metadata', {}).get('doc_type') == 'text'])}")
        print(f"  - 표: {len([r for r in top_results if r.get('metadata', {}).get('doc_type') == 'table'])}")
        print(f"  - 이미지: {len([r for r in top_results if r.get('metadata', {}).get('doc_type') == 'image'])}")
        
        return full_context
    
    def generate_answer(self, query: str, context: str, 
                       temperature: float = 0.3,
                       max_tokens: int = 2000) -> Optional[str]:
        """
        LLM으로 최종 답변 생성 (텍스트 답변)
        
        Args:
            query: 사용자 질문
            context: 구조화된 컨텍스트
            temperature: 온도 (0.0-2.0)
            max_tokens: 최대 토큰 수
        
        Returns:
            텍스트 답변
        """
        user_prompt = f"""{context}

사용자 질문: {query}

위 컨텍스트를 기반으로 사용자 질문에 답변해주세요.
출처 번호 [1], [2] 등을 명시하세요."""

        try:
            print(f"\n🤖 LLM 호출 중... (모델: {self.model})")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            usage = response.usage
            print(f"✓ LLM 응답 완료")
            print(f"  - 입력 토큰: {usage.prompt_tokens}")
            print(f"  - 출력 토큰: {usage.completion_tokens}")
            print(f"  - 총 토큰: {usage.total_tokens}")
            
            return answer
            
        except Exception as e:
            print(f"✗ LLM 호출 실패: {e}")
            return None
    
    def answer_question(self, query: str, search_results: List[Dict],
                       rewrite: bool = True) -> str:
        """
        질문에 답변하는 전체 파이프라인 (텍스트 답변)
        
        Args:
            query: 사용자 질문
            search_results: 검색 결과
            rewrite: 쿼리 리라이팅 사용 여부
        
        Returns:
            텍스트 답변
        """
        print("\n" + "="*80)
        print(f"❓ 질문: {query}")
        print("="*80)
        
        # 1. 쿼리 리라이팅 (선택)
        if rewrite:
            query = self.rewrite_query(query)
        
        # 2. 컨텍스트 구성
        context = self.build_context(search_results)
        
        # 3. LLM 답변 생성
        answer = self.generate_answer(query, context)
        
        if not answer:
            return "답변 생성에 실패했습니다."
        
        # 4. 결과 출력
        print("\n" + "="*80)
        print("💡 답변:")
        print("="*80)
        print(answer)
        print("="*80)
        
        return answer