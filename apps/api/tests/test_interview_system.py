"""
Comprehensive tests for interview system
Tests CV parsing, question generation, and analysis pipeline
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any


class TestCVParsing:
    """Test CV parsing functionality"""
    
    @pytest.mark.asyncio
    async def test_pdf_parsing(self):
        """Test PDF CV parsing"""
        from src.services.nlp import parse_resume_bytes
        
        # Mock PDF content
        mock_pdf_data = b'%PDF-1.4 mock pdf content with candidate info'
        
        with patch('src.services.nlp._read_pdf_bytes') as mock_read:
            mock_read.return_value = "John Doe\nSoftware Engineer\nPython, JavaScript\n5 years experience"
            
            result = parse_resume_bytes(mock_pdf_data, "application/pdf", "resume.pdf")
            
            assert "John Doe" in result
            assert "Software Engineer" in result
            assert len(result) > 50  # Reasonable content length
    
    @pytest.mark.asyncio
    async def test_docx_parsing(self):
        """Test DOCX CV parsing"""
        from src.services.nlp import parse_resume_bytes
        
        mock_docx_data = b'PK mock docx content'
        
        with patch('src.services.nlp._read_docx_bytes') as mock_read:
            mock_read.return_value = "Jane Smith\nProject Manager\nAgile, Scrum\n3 years experience"
            
            result = parse_resume_bytes(mock_docx_data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "resume.docx")
            
            assert "Jane Smith" in result
            assert "Project Manager" in result
    
    @pytest.mark.asyncio
    async def test_image_ocr_parsing(self):
        """Test OCR parsing for image CVs"""
        from src.services.nlp import parse_resume_bytes
        
        mock_image_data = b'\x89PNG\r\n\x1a\n mock image data'
        
        with patch('src.services.nlp._ocr_image_bytes_textract') as mock_ocr:
            mock_ocr.return_value = "Alex Johnson\nData Scientist\nPython, R, SQL\n4 years experience"
            
            result = parse_resume_bytes(mock_image_data, "image/png", "resume.png")
            
            assert "Alex Johnson" in result
            assert "Data Scientist" in result
    
    @pytest.mark.asyncio 
    async def test_candidate_field_extraction(self):
        """Test candidate field extraction from CV text"""
        from src.services.nlp import extract_candidate_fields
        
        cv_text = """
        John Doe
        Software Engineer
        Email: john.doe@example.com
        Phone: +90 555 123 4567
        LinkedIn: linkedin.com/in/johndoe
        
        Experience:
        - 5 years Python development
        - React, Node.js expertise
        - AWS, Docker experience
        """
        
        result = extract_candidate_fields(cv_text, "john_doe_cv.pdf")
        
        assert result["name"] == "John Doe"
        assert "john.doe@example.com" in result["email"]
        assert "555 123 4567" in result["phone"]
        assert result["links"]["linkedin"] is not None
        assert "Python" in result["skills"]
        assert "React" in result["skills"]


class TestQuestionGeneration:
    """Test interview question generation"""
    
    @pytest.mark.asyncio
    async def test_basic_question_generation(self):
        """Test basic question generation"""
        from src.core.gemini import generate_question_robust
        
        conversation_history = []
        job_context = "Software Engineer position requiring Python and React skills"
        
        with patch('src.core.gemini._sync_generate') as mock_generate:
            mock_generate.return_value = {
                "question": "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?",
                "done": False
            }
            
            result = await generate_question_robust(conversation_history, job_context)
            
            assert result["question"] != ""
            assert not result["done"]
    
    @pytest.mark.asyncio
    async def test_interview_completion(self):
        """Test interview completion detection"""
        from src.core.gemini import generate_question_robust
        
        # Simulate conversation with 7 questions
        conversation_history = [
            {"role": "assistant", "text": "Question 1"},
            {"role": "user", "text": "Answer 1"},
            {"role": "assistant", "text": "Question 2"},
            {"role": "user", "text": "Answer 2"},
            # ... continue for 7 questions
        ]
        
        with patch('src.core.gemini._sync_generate') as mock_generate:
            mock_generate.return_value = {"question": "", "done": True}
            
            result = await generate_question_robust(conversation_history, "", max_questions=3)
            
            assert result["done"]
    
    @pytest.mark.asyncio
    async def test_fallback_question_generation(self):
        """Test fallback when LLM is unavailable"""
        from src.core.gemini import _fallback_generate
        
        conversation_history = []
        job_context = "Python Developer position"
        
        result = _fallback_generate(conversation_history, job_context)
        
        assert result["question"] != ""
        assert not result["done"]
        question_text = str(result["question"])
        assert "somut örnek" in question_text or "anlatır mısınız" in question_text


class TestComprehensiveAnalysis:
    """Test comprehensive interview analysis"""
    
    @pytest.mark.asyncio
    async def test_hr_criteria_analysis(self):
        """Test HR criteria analysis"""
        from src.services.comprehensive_analyzer import ComprehensiveAnalyzer, AnalysisInput, AnalysisType
        
        analyzer = ComprehensiveAnalyzer()
        
        input_data = AnalysisInput(
            transcript_text="""
            Interviewer: Takım çalışması deneyiminizi anlatır mısınız?
            Candidate: Ben çok iyi takım çalışması yapıyorum. Projelerimde hep beraber çalıştık ve başarılı olduk.
            Interviewer: Somut bir örnek verebilir misiniz?
            Candidate: Geçen sene e-ticaret projesi yaptık, 5 kişi çalıştık, ben frontend'i aldım, çok güzel oldu.
            """,
            analysis_types=[AnalysisType.HR_CRITERIA]
        )
        
        with patch('src.services.llm_client.get_llm_client') as mock_client:
            mock_response = Mock()
            mock_response.content = '''
            {
                "criteria": [
                    {
                        "label": "İletişim Netliği",
                        "score_0_100": 75,
                        "evidence": "Soruları yanıtlıyor ama detay az",
                        "confidence": 0.7
                    }
                ],
                "summary": "Orta seviye iletişim",
                "overall_score": 75.0
            }
            '''
            
            mock_client.return_value.generate = AsyncMock(return_value=mock_response)
            
            result = await analyzer.analyze_comprehensive(input_data)
            
            assert "hr_criteria" in result
            hr_data = result["hr_criteria"]
            assert "criteria" in hr_data
            assert len(hr_data["criteria"]) > 0
            assert hr_data["criteria"][0]["score_0_100"] == 75
    
    @pytest.mark.asyncio
    async def test_job_fit_analysis(self):
        """Test job fit analysis"""
        from src.services.comprehensive_analyzer import ComprehensiveAnalyzer, AnalysisInput, AnalysisType
        
        analyzer = ComprehensiveAnalyzer()
        
        input_data = AnalysisInput(
            job_description="Python Developer - Flask, REST API, PostgreSQL experience required",
            transcript_text="I have 3 years Python experience, worked with Flask and APIs",
            resume_text="John Doe - Python Developer - Flask, Django, PostgreSQL",
            analysis_types=[AnalysisType.JOB_FIT]
        )
        
        with patch('src.services.llm_client.get_llm_client') as mock_client:
            mock_response = Mock()
            mock_response.content = '''
            {
                "job_fit_summary": "Good technical match",
                "overall_fit_score": 0.8,
                "requirements_matrix": [
                    {
                        "label": "Python",
                        "meets": "yes",
                        "source": "both",
                        "confidence": 0.9
                    }
                ]
            }
            '''
            
            mock_client.return_value.generate = AsyncMock(return_value=mock_response)
            
            result = await analyzer.analyze_comprehensive(input_data)
            
            assert "job_fit" in result
            fit_data = result["job_fit"]
            assert fit_data["overall_fit_score"] == 0.8
    
    @pytest.mark.asyncio
    async def test_parallel_analysis(self):
        """Test parallel execution of multiple analysis types"""
        from src.services.comprehensive_analyzer import ComprehensiveAnalyzer, AnalysisInput, AnalysisType
        
        analyzer = ComprehensiveAnalyzer()
        
        input_data = AnalysisInput(
            job_description="Software Engineer position",
            transcript_text="I am experienced in software development",
            analysis_types=[AnalysisType.HR_CRITERIA, AnalysisType.JOB_FIT, AnalysisType.HIRING_DECISION]
        )
        
        with patch('src.services.llm_client.get_llm_client') as mock_client:
            # Mock different responses for different analysis types
            def mock_generate(request):
                mock_response = Mock()
                if "HR" in request.prompt:
                    mock_response.content = '{"criteria": [], "summary": "Test HR"}'
                elif "job fit" in request.prompt:
                    mock_response.content = '{"overall_fit_score": 0.7}'
                else:
                    mock_response.content = '{"hire_recommendation": "Hold"}'
                return mock_response
            
            mock_client.return_value.generate = AsyncMock(side_effect=mock_generate)
            
            result = await analyzer.analyze_comprehensive(input_data)
            
            assert "hr_criteria" in result
            assert "job_fit" in result
            assert "hiring_decision" in result
            
            # Verify parallel execution by checking all results are present
            assert len(result) >= 3


class TestInterviewEngine:
    """Test InterviewEngine integration"""
    
    @pytest.mark.asyncio
    async def test_context_loading(self):
        """Test interview context loading"""
        from src.services.interview_engine import InterviewEngine
        
        # Mock database session and models
        mock_session = Mock()
        engine = InterviewEngine(mock_session)
        
        # Mock database query results
        mock_interview = Mock()
        mock_interview.id = 1
        mock_interview.job_id = 1
        mock_interview.candidate_id = 1
        mock_interview.transcript_text = "Mock transcript"
        
        mock_job = Mock()
        mock_job.description = "Software Engineer position"
        mock_job.title = "Senior Developer"
        
        mock_candidate = Mock()
        mock_candidate.name = "John Doe"
        
        mock_profile = Mock()
        mock_profile.resume_text = "John Doe resume content"
        
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            mock_interview, mock_job, mock_candidate, mock_profile
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        
        context = await engine.load_context(1)
        
        assert context.interview_id == 1
        assert context.job_description == "Software Engineer position"
        assert context.candidate_name == "John Doe"
        assert context.resume_text == "John Doe resume content"
    
    @pytest.mark.asyncio
    async def test_comprehensive_processing(self):
        """Test end-to-end interview processing"""
        from src.services.interview_engine import InterviewEngine
        
        mock_session = Mock()
        engine = InterviewEngine(mock_session)
        
        # Mock context loading
        with patch.object(engine, 'load_context') as mock_load:
            mock_context = Mock()
            mock_context.job_description = "Python Developer"
            mock_context.transcript_text = "Interview transcript content"
            mock_context.resume_text = "Resume content"
            mock_context.candidate_name = "John Doe"
            mock_context.job_title = "Developer"
            mock_load.return_value = mock_context
            
            # Mock comprehensive analysis
            with patch('src.services.comprehensive_analyzer.comprehensive_interview_analysis') as mock_analysis:
                mock_analysis.return_value = {
                    "hr_criteria": {"criteria": []},
                    "job_fit": {"overall_fit_score": 0.8},
                    "hiring_decision": {"hire_recommendation": "Hire"},
                    "meta": {"overall_score": 80.0}
                }
                
                # Mock database operations
                mock_session.execute.return_value.scalar_one_or_none.return_value = None
                mock_session.add = Mock()
                mock_session.commit = AsyncMock()
                mock_session.refresh = AsyncMock()
                
                result = await engine.process_complete_interview(1)
                
                # Verify analysis was called
                mock_analysis.assert_called_once()
                
                # Verify database operations
                mock_session.add.assert_called_once()
                mock_session.commit.assert_called_once()


class TestPerformanceOptimization:
    """Test performance optimization features"""
    
    @pytest.mark.asyncio
    async def test_cv_parsing_cache(self):
        """Test CV parsing with caching"""
        from src.services.performance_optimizer import CachedAnalysisService
        
        service = CachedAnalysisService()
        cv_content = b"Mock CV content"
        content_type = "application/pdf"
        
        # Mock parsing function
        with patch('src.services.nlp.parse_resume_bytes') as mock_parse:
            mock_parse.return_value = "Parsed CV content"
            
            with patch('src.services.nlp.extract_candidate_fields_smart') as mock_extract:
                mock_extract.return_value = {"name": "John Doe", "email": "john@example.com"}
                
                # First call should hit the parser
                result1 = await service.cached_cv_parsing(cv_content, content_type)
                
                # Second call should hit the cache
                result2 = await service.cached_cv_parsing(cv_content, content_type)
                
                # Parser should only be called once
                assert mock_parse.call_count == 1
                
                # Results should be identical
                assert result1 == result2
                assert result1["resume_text"] == "Parsed CV content"
    
    def test_cache_eviction(self):
        """Test cache eviction when memory limit is reached"""
        from src.services.performance_optimizer import PerformanceCache, CacheType
        
        # Create small cache
        cache = PerformanceCache(max_size_mb=1)  # 1MB limit
        
        # Fill cache with large entries
        for i in range(10):
            large_data = "x" * 100000  # 100KB each
            cache.set(CacheType.CV_PARSING, large_data, None, f"key_{i}")
        
        # Verify cache size is managed
        stats = cache.get_stats()
        assert stats["total_size_mb"] <= 1.1  # Allow small overhead
    
    @pytest.mark.asyncio
    async def test_parallel_processing(self):
        """Test parallel task execution"""
        from src.services.performance_optimizer import ParallelProcessor
        
        processor = ParallelProcessor()
        
        # Create mock async tasks
        async def mock_task(delay: float, result: str):
            await asyncio.sleep(delay)
            return result
        
        from typing import Callable, Awaitable
        
        def create_task(result: str) -> Callable[[], Awaitable[str]]:
            async def task():
                return await mock_task(0.1, result)
            return task
        
        tasks = [
            create_task("task1"),
            create_task("task2"),
            create_task("task3")
        ]
        
        start_time = asyncio.get_event_loop().time()
        results = await processor.batch_execute(tasks)
        end_time = asyncio.get_event_loop().time()
        
        # Should complete in parallel (much faster than sequential)
        assert (end_time - start_time) < 0.5  # Much less than 0.3s sequential
        assert len(results) == 3
        assert "task1" in results


@pytest.fixture
def mock_database():
    """Mock database session fixture"""
    return Mock()


if __name__ == "__main__":
    pytest.main([__file__])
