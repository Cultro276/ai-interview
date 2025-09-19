"""
UNIFIED REPORTING ENGINE
Comprehensive interview report generation with all visualization data and export formats
Consolidates all report features into single backend service
"""
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
import math
from src.core.config import settings


class InterviewReportGenerator:
    """Generate structured, professional interview reports with multiple output formats"""
    
    def __init__(self):
        self.templates = {
            "executive_summary": self._executive_summary_template,
            "detailed_technical": self._detailed_technical_template,
            "behavioral_focus": self._behavioral_focus_template,
            "hiring_decision": self._hiring_decision_template,
            # Turkish HR detailed structure per product spec
            "turkish_hr": self._turkish_hr_template,
        }
    
    def generate_comprehensive_report(self, 
                                    interview_data: Dict[str, Any], 
                                    analysis_results: Dict[str, Any],
                                    template_type: str = "executive_summary") -> Dict[str, Any]:
        """Generate comprehensive interview report using specified template"""
        
        template_func = self.templates.get(template_type, self._executive_summary_template)
        
        report = {
            "metadata": {
                "interview_id": interview_data.get("id"),
                "candidate_name": interview_data.get("candidate_name", "Unknown"),
                "position": interview_data.get("job_title", "Unknown"),
                "interview_date": interview_data.get("created_at", datetime.now().isoformat()),
                "report_generated": datetime.now().isoformat(),
                "template_type": template_type,
                "report_version": "2.0"
            },
            "content": template_func(interview_data, analysis_results),
            "scoring": self._extract_scoring_summary(analysis_results),
            "recommendations": self._generate_recommendations(analysis_results),
            "visualization_data": self._generate_visualization_data(analysis_results), # ✅ ADD UI DATA
            "export_formats": {
                "json": True,
                "markdown": True,
                "pdf_ready": True
            }
        }
        
        return report

    def _turkish_hr_template(self, interview_data: Dict, analysis: Dict) -> Dict[str, Any]:
        """Detailed Turkish HR report matching requested headings"""
        # Gather inputs
        job_fit = analysis.get("job_fit", {})
        ai_opinion = analysis.get("ai_opinion", {})
        multipass = analysis.get("multipass_analysis", {})
        hr_criteria = analysis.get("hr_criteria", {})

        overall_score_0_100 = None
        try:
            meta = analysis.get("meta", {})
            ov = meta.get("overall_score")
            if isinstance(ov, (int, float)):
                overall_score_0_100 = round(float(ov), 2)
        except Exception:
            overall_score_0_100 = None

        # Summaries
        intro_summary = (
            analysis.get("hiring_decision", {}).get("overall_assessment")
            or job_fit.get("job_fit_summary")
            or ""
        )

        # Strengths / Weaknesses
        strengths = (ai_opinion.get("key_strengths") or [])[:5]
        weaknesses = (job_fit.get("clear_gaps") or [])[:5]

        # Technical assessment mapping
        requirements_matrix = job_fit.get("requirements_matrix", [])
        tech_strengths = []
        tech_weak = []
        try:
            for r in requirements_matrix:
                meets = str(r.get("meets", "")).lower()
                label = r.get("label", "")
                if meets == "yes":
                    tech_strengths.append(label)
                elif meets in ("partial", "no"):
                    tech_weak.append(label)
        except Exception:
            pass

        # Cultural / behavioral
        cultural = multipass.get("overall_scores", {}).get("cultural", 0.5)
        behavioral_avg = self._calculate_behavioral_average(hr_criteria)

        # Communication score approximation
        comm_0_100 = hr_criteria.get("overall_score", 50)

        # Fit score 0–100
        fit_score = None
        try:
            fit_score = round(float(job_fit.get("overall_fit_score", 0.5)) * 100, 2)
        except Exception:
            fit_score = None

        # Final recommendation
        decision = ai_opinion.get("hire_recommendation", "Hold")
        decision_tr = self._translate_recommendation(decision)
        recommendation_reason = ai_opinion.get("overall_assessment", "")

        # Determine recommended next interview types
        next_types = self._compute_next_interview_types(analysis)

        return {
            "genel_aday_ozeti": {
                "pozisyon": interview_data.get("job_title"),
                "deneyim_seviyesi": interview_data.get("experience_level"),
                "egitim": interview_data.get("education_level"),
                "tanitim_ozeti": (intro_summary or "").strip()[:400],
            },
            "guclu_yonler": strengths or tech_strengths,
            "gelisim_alanlari": weaknesses or tech_weak,
            "teknik_yeterlilik": {
                "guc": tech_strengths[:8],
                "zayif": tech_weak[:8],
                "orneksel_not": "Örnek: Finansal raporlama güçlü, IFRS bilgisi yüzeysel" if tech_weak else "",
            },
            "davranissal_kulturel_uyum": {
                "ekip_uyumu": behavioral_avg,
                "kultur_uyumu": cultural,
                "turkiye_piyasa_beklentisi": "Esneklik ve iş disiplini açısından genel uyum değerlendirildi",
            },
            "iletisim_becerileri": {
                "netlik": comm_0_100 / 100,
                "tutarlilik": behavioral_avg,
                "not": "Analiz sadece içerik üzerinden yapılmıştır; aksan/fiziksel özellikler raporlanmaz.",
            },
            "tutarlilik_analizi": {
                "cv_mulkakat_uyumu": requirements_matrix,
                "cakisiyor_gorunen": weaknesses[:3] if isinstance(weaknesses, list) else [],
            },
            "onerilen_sonraki_adimlar": next_types,
            "uygunluk_skoru": fit_score if fit_score is not None else overall_score_0_100,
            "nihai_oneri": {
                "onerilen_aksiyon": decision_tr,
                "gerekce": (recommendation_reason or "")[:200],
                "onerilen_sonraki_adimlar": next_types,
            },
        }
    
    def _executive_summary_template(self, interview_data: Dict, analysis: Dict) -> Dict[str, Any]:
        """Executive summary template for senior leadership"""
        
        hr_criteria = analysis.get("hr_criteria", {})
        job_fit = analysis.get("job_fit", {})
        ai_opinion = analysis.get("ai_opinion", {})
        multipass = analysis.get("multipass_analysis", {})
        ta = analysis.get("technical_assessment", {})
        if isinstance(ta, str):
            try:
                import json
                ta = json.loads(ta)
            except Exception:
                ta = {}
        cv_facts = ta.get("cv_facts", {})
        # Only show military status when explicitly relevant to the role/requirements
        show_military = False
        try:
            reqs = job_fit.get("requirements_matrix", []) if isinstance(job_fit, dict) else []
            if isinstance(reqs, list):
                for r in reqs:
                    try:
                        label = (r.get("label", "") or "").lower()
                        if "asker" in label:  # asker/askerlik/tecilli
                            show_military = True
                            break
                    except Exception:
                        continue
        except Exception:
            show_military = False
        
        return {
            "executive_overview": {
                "recommendation": ai_opinion.get("hire_recommendation", "Hold"),
                "confidence": ai_opinion.get("decision_confidence", 0.5),
                "key_verdict": self._create_verdict_statement(ai_opinion),
                "risk_level": self._assess_risk_level(ai_opinion.get("risk_factors", []))
            },
            **({
                "profile_facts": {
                    "military_status": cv_facts.get("military_status", "bilinmiyor"),
                }
            } if show_military and cv_facts.get("military_status") not in (None, "bilinmiyor") else {}),
            "competency_scores": {
                "technical_fit": job_fit.get("overall_fit_score", 0.5),
                "behavioral_strength": self._calculate_behavioral_average(hr_criteria),
                "cultural_alignment": multipass.get("overall_scores", {}).get("cultural", 0.5),
                "growth_potential": ai_opinion.get("skill_match", {}).get("growth_potential", 0.5)
            },
            "critical_highlights": {
                "top_strengths": ai_opinion.get("key_strengths", [])[:3],
                "main_concerns": ai_opinion.get("key_concerns", [])[:3],
                "standout_evidence": self._extract_standout_evidence(analysis)
            },
            "business_impact": {
                "time_to_productivity": self._estimate_ramp_time(analysis),
                "team_fit_score": multipass.get("overall_scores", {}).get("behavioral", 0.5),
                "retention_indicators": self._assess_retention_risk(analysis)
            }
        }
    
    def _detailed_technical_template(self, interview_data: Dict, analysis: Dict) -> Dict[str, Any]:
        """Detailed technical assessment template"""
        
        job_fit = analysis.get("job_fit", {})
        multipass = analysis.get("multipass_analysis", {})
        technical_analysis = multipass.get("technical", {})
        # Sort requirements: high importance first
        reqs = job_fit.get("requirements_matrix", [])
        try:
            def _imp_val(v: str) -> int:
                low = (v or "").lower()
                return 2 if low == "high" else 1 if low == "medium" else 0
            reqs_sorted = sorted(reqs, key=lambda r: _imp_val(r.get("importance", "medium")), reverse=True)
        except Exception:
            reqs_sorted = reqs
        
        return {
            "technical_assessment": {
                "overall_score": technical_analysis.get("technical_score", 0.5),
                "problem_solving": technical_analysis.get("problem_solving_score", 0.5),
                "architecture_understanding": technical_analysis.get("architecture_understanding", 0.5),
                "technology_depth": technical_analysis.get("technology_depth", 0.5)
            },
            "requirement_matrix": reqs_sorted,
            "technical_evidence": {
                "strong_areas": technical_analysis.get("standout_skills", []),
                "gap_areas": technical_analysis.get("technical_gaps", []),
                "evidence_quality": self._assess_evidence_quality(technical_analysis.get("evidence_items", []))
            },
            "coding_assessment": {
                "approach_quality": "Not assessed in this interview",
                "code_quality_indicators": [],
                "problem_decomposition": self._extract_problem_solving_evidence(technical_analysis)
            },
            "technology_stack": {
                "confirmed_skills": job_fit.get("cv_existing_skills", []),
                "demonstrated_skills": job_fit.get("interview_demonstrated", []),
                "skill_gaps": job_fit.get("clear_gaps", [])
            }
        }
    
    def _behavioral_focus_template(self, interview_data: Dict, analysis: Dict) -> Dict[str, Any]:
        """Behavioral competency focused template"""
        
        hr_criteria = analysis.get("hr_criteria", {})
        multipass = analysis.get("multipass_analysis", {})
        behavioral_analysis = multipass.get("behavioral", {})
        
        return {
            "behavioral_competencies": {
                "leadership": behavioral_analysis.get("leadership_score", 0.5),
                "teamwork": behavioral_analysis.get("teamwork_score", 0.5),
                "communication": behavioral_analysis.get("communication_score", 0.5),
                "adaptability": behavioral_analysis.get("adaptability_score", 0.5)
            },
            "star_evidence": behavioral_analysis.get("behavioral_evidence", []),
            "soft_skills_analysis": {
                "communication_style": self._analyze_communication_style(hr_criteria),
                "conflict_resolution": "Assess from STAR examples",
                "stress_management": "Evaluate from responses"
            },
            "cultural_indicators": {
                "value_alignment": multipass.get("cultural", {}).get("cultural_indicators", []),
                "growth_mindset": multipass.get("cultural", {}).get("growth_mindset_score", 0.5),
                "learning_agility": multipass.get("cultural", {}).get("learning_agility", 0.5)
            },
            "red_flags": behavioral_analysis.get("red_flags", []),
            "behavioral_strengths": behavioral_analysis.get("behavioral_strengths", [])
        }
    
    def _hiring_decision_template(self, interview_data: Dict, analysis: Dict) -> Dict[str, Any]:
        """Hiring decision focused template with actionable recommendations"""
        
        ai_opinion = analysis.get("ai_opinion", {})
        job_fit = analysis.get("job_fit", {})
        
        return {
            "hiring_recommendation": {
                "decision": ai_opinion.get("hire_recommendation", "Hold"),
                "confidence_level": ai_opinion.get("decision_confidence", 0.5),
                "timeline": ai_opinion.get("timeline_recommendation", "reassess"),
                "decision_rationale": ai_opinion.get("overall_assessment", "")
            },
            "compensation_analysis": ai_opinion.get("salary_analysis", {}),
            "onboarding_plan": {
                "skill_development_areas": job_fit.get("clear_gaps", [])[:3],
                "mentor_assignment": "Recommend technical mentor" if job_fit.get("overall_fit_score", 0) < 0.7 else "Standard onboarding",
                "90_day_goals": self._suggest_90_day_goals(analysis)
            },
            "risk_mitigation": {
                "identified_risks": ai_opinion.get("risk_factors", []),
                "mitigation_strategies": ai_opinion.get("mitigation_strategies", []),
                "success_indicators": self._define_success_metrics(analysis)
            },
            "team_integration": {
                "team_fit_score": analysis.get("multipass_analysis", {}).get("overall_scores", {}).get("behavioral", 0.5),
                "collaboration_style": "Extract from behavioral evidence",
                "management_style_preference": "Assess from responses"
            }
        }
    
    def _extract_scoring_summary(self, analysis: Dict) -> Dict[str, float]:
        """Extract and normalize key scores"""
        
        hr_criteria = analysis.get("hr_criteria", {})
        job_fit = analysis.get("job_fit", {})
        ai_opinion = analysis.get("ai_opinion", {})
        multipass = analysis.get("multipass_analysis", {})
        
        return {
            "Genel Öneri Skoru": self._recommendation_to_score(ai_opinion.get("hire_recommendation", "Hold")),
            "Teknik Yetkinlik": job_fit.get("overall_fit_score", 0.5),
            "Davranışsal Yetkinlik": self._calculate_behavioral_average(hr_criteria),
            "Kültürel Uyum": multipass.get("overall_scores", {}).get("cultural", 0.5),
            "İletişim Etkinliği": hr_criteria.get("overall_score", 50) / 100,
            "Büyüme Potansiyeli": ai_opinion.get("skill_match", {}).get("growth_potential", 0.5),
            "Karar Güveni": ai_opinion.get("decision_confidence", 0.5)
        }
    
    def _generate_recommendations(self, analysis: Dict) -> Dict[str, List[str]]:
        """Generate actionable recommendations"""
        
        ai_opinion = analysis.get("ai_opinion", {})
        job_fit = analysis.get("job_fit", {})
        
        return {
            "immediate_actions": ai_opinion.get("next_steps", []),
            "skill_development": job_fit.get("clear_gaps", [])[:3],
            "interview_process": [
                "Consider technical coding session" if job_fit.get("overall_fit_score", 0) < 0.7 else "Technical assessment complete",
                "Schedule team interview" if analysis.get("multipass_analysis", {}).get("overall_scores", {}).get("behavioral", 0) > 0.7 else "Focus on cultural fit assessment"
            ],
            "onboarding_focus": job_fit.get("recommendations", [])[:3]
        }
    
    # Utility methods
    def _create_verdict_statement(self, ai_opinion: Dict) -> str:
        """Create executive verdict statement"""
        recommendation = ai_opinion.get("hire_recommendation", "Hold")
        confidence = ai_opinion.get("decision_confidence", 0.5)
        
        confidence_text = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
        
        statements = {
            "Strong Hire": f"Strong candidate with {confidence_text} confidence - proceed immediately",
            "Hire": f"Solid candidate with {confidence_text} confidence - recommend offer",
            "Hold": f"Mixed signals with {confidence_text} confidence - requires additional assessment",
            "No Hire": f"Not suitable with {confidence_text} confidence - decline respectfully"
        }
        
        return statements.get(recommendation, "Assessment incomplete")
    
    def _assess_risk_level(self, risk_factors: List[str]) -> str:
        """Assess overall risk level"""
        if len(risk_factors) == 0:
            return "Low"
        elif len(risk_factors) <= 2:
            return "Medium" 
        else:
            return "High"
    
    def _calculate_behavioral_average(self, hr_criteria: Dict) -> float:
        """Calculate average behavioral score"""
        criteria = hr_criteria.get("criteria", [])
        if not criteria:
            return 0.5
        
        scores = [c.get("score_0_100", 50) for c in criteria]
        return sum(scores) / len(scores) / 100
    
    def _extract_standout_evidence(self, analysis: Dict) -> List[str]:
        """Extract most compelling evidence"""
        evidence = []
        
        # Get technical evidence
        technical = analysis.get("multipass_analysis", {}).get("technical", {})
        for item in technical.get("evidence_items", [])[:2]:
            if item.get("strength_level") == "strong":
                evidence.append(f"Technical: {item.get('evidence', '')}")
        
        # Get behavioral evidence  
        behavioral = analysis.get("multipass_analysis", {}).get("behavioral", {})
        for item in behavioral.get("behavioral_evidence", [])[:2]:
            if item.get("star_completeness", 0) > 0.8:
                evidence.append(f"Behavioral: {item.get('situation', '')}")
        
        return evidence[:3]
    
    def _estimate_ramp_time(self, analysis: Dict) -> str:
        """Estimate time to productivity"""
        job_fit_score = analysis.get("job_fit", {}).get("overall_fit_score", 0.5)
        
        if job_fit_score > 0.8:
            return "1-2 months"
        elif job_fit_score > 0.6:
            return "2-4 months"
        else:
            return "4-6 months"
    
    def _assess_retention_risk(self, analysis: Dict) -> str:
        """Assess retention risk indicators"""
        cultural_fit = analysis.get("multipass_analysis", {}).get("overall_scores", {}).get("cultural", 0.5)
        growth_potential = analysis.get("ai_opinion", {}).get("skill_match", {}).get("growth_potential", 0.5)
        
        if cultural_fit > 0.7 and growth_potential > 0.7:
            return "Low - strong cultural fit and growth mindset"
        elif cultural_fit < 0.5 or growth_potential < 0.4:
            return "High - cultural or growth concerns"
        else:
            return "Medium - monitor cultural integration"
    
    def _assess_evidence_quality(self, evidence_items: List[Dict]) -> str:
        """Assess quality of technical evidence"""
        if not evidence_items:
            return "Limited"
        
        strong_count = sum(1 for item in evidence_items if item.get("strength_level") == "strong")
        return "Strong" if strong_count >= 2 else "Moderate" if strong_count >= 1 else "Weak"
    
    def _extract_problem_solving_evidence(self, technical_analysis: Dict) -> List[str]:
        """Extract problem solving approach evidence"""
        evidence = []
        for item in technical_analysis.get("evidence_items", []):
            if item.get("category") == "problem_solving":
                evidence.append(item.get("evidence", ""))
        return evidence[:3]
    
    def _analyze_communication_style(self, hr_criteria: Dict) -> str:
        """Analyze communication style from HR criteria"""
        criteria = hr_criteria.get("criteria", [])
        comm_criterion = next((c for c in criteria if "iletişim" in c.get("label", "").lower()), {})
        
        score = comm_criterion.get("score_0_100", 50)
        if score > 80:
            return "Excellent - clear, structured, engaging"
        elif score > 60:
            return "Good - adequate clarity and structure"
        else:
            return "Needs improvement - unclear or unstructured"
    
    def _suggest_90_day_goals(self, analysis: Dict) -> List[str]:
        """Suggest 90-day goals based on analysis"""
        gaps = analysis.get("job_fit", {}).get("clear_gaps", [])
        return [f"Develop proficiency in {gap}" for gap in gaps[:3]]
    
    def _define_success_metrics(self, analysis: Dict) -> List[str]:
        """Define success metrics for the role"""
        return [
            "Complete onboarding technical assessments",
            "Integrate successfully with team",
            "Deliver first project milestone"
        ]
    
    def _recommendation_to_score(self, recommendation: str) -> float:
        """Convert recommendation to numeric score"""
        mapping = {
            "Strong Hire": 0.95,
            "Hire": 0.75,
            "Hold": 0.5,
            "No Hire": 0.25
        }
        return mapping.get(recommendation, 0.5)
    
    def generate_competency_radar_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate competency radar chart data"""
        scores = analysis.get("comprehensive_report", {}).get("content", {}).get("competency_scores", {})
        if not scores:
            # Fallback to individual scores
            scores = {
                "technical_competency": analysis.get("job_fit", {}).get("overall_fit_score", 0.5),
                "communication": analysis.get("communication_score", 0) / 100 if analysis.get("communication_score") else 0.5,
                "cultural_fit": analysis.get("cultural_fit_score", 0) / 100 if analysis.get("cultural_fit_score") else 0.5,
                "behavioral_strength": self._calculate_behavioral_average(analysis.get("hr_criteria", {})),
                "growth_potential": analysis.get("ai_opinion", {}).get("skill_match", {}).get("growth_potential", 0.5),
                "team_collaboration": analysis.get("multipass_analysis", {}).get("overall_scores", {}).get("behavioral", 0.5)
            }
        
        competencies = []
        for key, score in scores.items():
            competency_name = key.replace('_', ' ').title()
            normalized_score = float(score) * 100 if float(score) <= 1 else float(score)
            level = "expert" if normalized_score > 80 else "proficient" if normalized_score > 60 else "basic" if normalized_score > 40 else "none"
            
            competencies.append({
                "competency": competency_name,
                "score": round(normalized_score),
                "benchmark": 70,
                "level": level
            })
        
        return {
            "competencies": competencies,
            "title": "360° Yetkinlik Analizi",
            "chart_data": {
                "labels": [c["competency"] for c in competencies],
                "candidate_scores": [c["score"] for c in competencies],
                "benchmark_scores": [c["benchmark"] for c in competencies],
                "levels": [c["level"] for c in competencies]
            }
        }
    
    def generate_evidence_based_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate evidence-based analysis data"""
        ta = analysis.get("technical_assessment", {})
        if isinstance(ta, str):
            try:
                ta = json.loads(ta)
            except:
                ta = {}
        
        job_fit = ta.get("job_fit", {})
        requirements_matrix = job_fit.get("requirements_matrix", [])
        
        # Include panel review and work samples if available
        panel = ta.get("panel_review") or {}
        work_samples = ta.get("work_samples") or []

        # Convert requirements to evidence items
        evidence_items = []
        for req in requirements_matrix:
            confidence = 90 if req.get("meets") == "yes" else 65 if req.get("meets") == "partial" else 40
            status = "verified" if req.get("meets") == "yes" else "needs_verification" if req.get("meets") == "partial" else "conflicting"
            
            evidence_items.append({
                "claim": req.get("label", ""),
                "evidence_quotes": [req.get("evidence", "")] if req.get("evidence") else [],
                "confidence_level": confidence,
                "verification_status": status
            })
        
        # Generate behavioral patterns from HR criteria
        behavioral_patterns = []
        hr_criteria = analysis.get("hr_criteria", {}).get("criteria", [])
        for criterion in hr_criteria:
            if criterion.get("evidence"):
                score = criterion.get("score_0_100", 50)
                impact = "positive" if score > 70 else "negative" if score < 40 else "neutral"
                
                behavioral_patterns.append({
                    "pattern": criterion.get("label", ""),
                    "frequency": 1,
                    "examples": [criterion.get("evidence", "")],
                    "impact": impact
                })
        
        # Generate competency evidence
        competency_evidence = []
        ai_opinion = ta.get("ai_opinion", {})
        if ai_opinion.get("key_strengths"):
            for strength in ai_opinion["key_strengths"]:
                competency_evidence.append({
                    "competency": "Güçlü Yönler",
                    "level": "proficient",
                    "supporting_quotes": [strength],
                    "behavioral_indicators": ["Positive performance indicator"]
                })
        # Add panel decision and work samples sections
        panel_section = {
            "decision": panel.get("decision"),
            "notes": panel.get("notes"),
            "rubric": panel.get("rubric") or []
        }
        work_samples_section = [
            {
                "name": ws.get("name"),
                "score_0_100": ws.get("score_0_100"),
                "weight_0_1": ws.get("weight_0_1"),
                "notes": ws.get("notes")
            } for ws in work_samples if isinstance(ws, dict)
        ]

        return {
            "evidence_items": evidence_items,
            "behavioral_patterns": behavioral_patterns,
            "competency_evidence": competency_evidence,
            "transcript": analysis.get("transcript", ""),
            "panel_review": panel_section,
            "work_samples": work_samples_section,
            "summary_stats": {
                "total_evidence_items": len(evidence_items),
                "verified_claims": len([e for e in evidence_items if e["verification_status"] == "verified"]),
                "high_confidence_items": len([e for e in evidence_items if e["confidence_level"] > 80])
            }
        }
    
    def _generate_visualization_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate visualization data structure for frontend UI components"""
        
        # Extract hiring decision data
        hiring_data = self.generate_hiring_decision_data(analysis)
        
        # Get AI opinion data
        ta = analysis.get("technical_assessment", {})
        if isinstance(ta, str):
            try:
                ta = json.loads(ta)
            except:
                ta = {}
        
        ai_opinion = ta.get("ai_opinion", {})
        job_fit = ta.get("job_fit", {})
        
        # Create the expected UI structure
        return {
            "hiring_decision": {
                "should_display": True,  # ✅ Enable UI display
                "hiring_recommendation": {
                    "decision_label": self._get_decision_label(ai_opinion.get("hire_recommendation", "Hold")),
                    "confidence": ai_opinion.get("decision_confidence", 0.5),
                    "color_scheme": self._get_decision_colors(ai_opinion.get("hire_recommendation", "Hold"))
                },
                "key_strengths": ai_opinion.get("key_strengths", ["Değerlendirme tamamlanırken güçlü yönler belirlenecek"]),
                "development_areas": job_fit.get("clear_gaps", ["Gelişim alanları analiz ediliyor"]),
                "onboarding_plan": hiring_data.get("onboarding_plan", {}),
                "risk_factors": ai_opinion.get("risk_factors", []),
                "salary_analysis": ai_opinion.get("salary_analysis", {}),
                "next_steps": ai_opinion.get("next_steps", ["Detaylı değerlendirme devam ediyor"])
            },
            "conversation_statistics": self._generate_conversation_stats(analysis),
            "competency_breakdown": self._generate_competency_visual_data(analysis)
        }
    
    def _get_decision_label(self, recommendation: str) -> str:
        """Convert recommendation to Turkish display label"""
        labels = {
            "Strong Hire": "Kesinlikle İşe Al",
            "Hire": "İşe Al", 
            "Hold": "Beklemede Tut",
            "No Hire": "İşe Alma"
        }
        return labels.get(recommendation, recommendation)
    
    def _get_decision_colors(self, recommendation: str) -> Dict[str, str]:
        """Get color scheme for decision"""
        colors = {
            "Strong Hire": {"bg": "bg-green-100", "text": "text-green-800"},
            "Hire": {"bg": "bg-blue-100", "text": "text-blue-800"},
            "Hold": {"bg": "bg-yellow-100", "text": "text-yellow-800"},
            "No Hire": {"bg": "bg-red-100", "text": "text-red-800"}
        }
        return colors.get(recommendation, {"bg": "bg-gray-100", "text": "text-gray-800"})
    
    def _generate_conversation_stats(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conversation statistics for display"""
        # TODO: Extract actual conversation metrics from transcript
        return {
            "candidate_talk_time_percentage": 75,
            "average_response_length": 45,
            "total_questions_asked": 6,
            "follow_up_questions": 3,
            "conversation_flow_score": 8.2
        }
    
    def _generate_competency_visual_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate competency breakdown for visual display"""
        # Use Turkish-labeled keys produced by _extract_scoring_summary
        scoring = self._extract_scoring_summary(analysis)
        def _val(key: str, default: float) -> float:
            try:
                v = float(scoring.get(key, default))
                # If value seems to be 0..1 ratio, convert to 0..100
                return v * 100.0 if v <= 1.0 else v
            except Exception:
                return default * 100.0
        return {
            "Teknik Yetkinlik": _val("Teknik Yetkinlik", 0.7),
            "İletişim Etkinliği": _val("İletişim Etkinliği", 0.8),
            "Davranışsal Yetkinlik": _val("Davranışsal Yetkinlik", 0.75),
            "Kültürel Uyum": _val("Kültürel Uyum", 0.85),
            "Büyüme Potansiyeli": _val("Büyüme Potansiyeli", 0.6),
        }

    def generate_hiring_decision_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured hiring decision data"""
        ta = analysis.get("technical_assessment", {})
        if isinstance(ta, str):
            try:
                ta = json.loads(ta)
            except:
                ta = {}
        
        ai_opinion = ta.get("ai_opinion", {})
        job_fit = ta.get("job_fit", {})
        
        # Extract and structure decision data
        hiring_recommendation = ai_opinion.get("hire_recommendation", "Hold")
        key_strengths = ai_opinion.get("key_strengths", [])
        key_concerns = ai_opinion.get("key_concerns", [])
        next_steps = ai_opinion.get("next_steps", [])
        risk_factors = ai_opinion.get("risk_factors", [])
        clear_gaps = job_fit.get("clear_gaps", [])
        
        # Adaptive onboarding plan based on gaps
        onboarding_plan = {
            "first_30_days": [
                "Teknik ekiple tanışma ve proje briefingleri",
                "Rol odaklı oryantasyon programı"
            ],
            "30_90_days": [
                "Rol-spesifik beceri geliştirme",
                "İlk proje teslimi ve geri bildirim"
            ],
            "90_plus_days": [
                "Performans değerlendirmesi",
                "Uzun vadeli hedef belirleme",
                "Kariyer yolu planlama"
            ]
        }
        
        # Add adaptive recommendations based on gaps
        if "communication" in str(clear_gaps + key_concerns).lower() or any("iletişim" in str(c).lower() for c in key_concerns):
            onboarding_plan["first_30_days"].append("İletişim becerileri atölyesi")
        else:
            onboarding_plan["first_30_days"].append("Takım dinamikleri tanıtımı")
            
        if "leadership" in str(clear_gaps + key_concerns).lower() or any("liderlik" in str(c).lower() for c in key_concerns):
            onboarding_plan["30_90_days"].insert(0, "Mentor ataması (liderlik gelişimi)")
        else:
            onboarding_plan["30_90_days"].insert(0, "Küçük projelerde sorumluluk alma")
        
        next_types = self._compute_next_interview_types(analysis)

        return {
            "hiring_recommendation": {
                "decision": hiring_recommendation,
                "decision_label": self._translate_recommendation(hiring_recommendation),
                "confidence": ai_opinion.get("decision_confidence", 0.5),
                "color_scheme": self._get_decision_colors(hiring_recommendation)
            },
            "key_strengths": key_strengths[:4],  # Limit to 4 most important
            "development_areas": (key_concerns[:2] + clear_gaps[:2])[:4],  # Combined, limited to 4
            "onboarding_plan": onboarding_plan,
            "next_steps": next_steps,
            "risk_factors": risk_factors,
            "timeline_recommendation": ai_opinion.get("timeline_recommendation", "reassess"),
            "salary_analysis": ai_opinion.get("salary_analysis", {}),
            "recommended_next_interview_types": next_types,
            "should_display": bool(hiring_recommendation or key_strengths or key_concerns)
        }
    
    def _translate_recommendation(self, recommendation: str) -> str:
        """Translate English recommendation to Turkish"""
        translations = {
            "Strong Hire": "Kesinlikle İşe Al",
            "Hire": "İşe Al", 
            "Hold": "Beklet",
            "No Hire": "İşe Alma"
        }
        return translations.get(recommendation, recommendation)

    def _compute_next_interview_types(self, analysis: Dict[str, Any]) -> List[str]:
        """Infer recommended next interview types from analysis signals.
        Returns a prioritized list with zero or more of:
        - "Teknik görüşme"
        - "Yönetici görüşmesi"
        - "İnsan kaynakları kültür uyum görüşmesi"
        """
        try:
            ta = analysis.get("technical_assessment", {})
            if isinstance(ta, str):
                try:
                    ta = json.loads(ta)
                except Exception:
                    ta = {}
            job_fit = analysis.get("job_fit", {}) if isinstance(analysis, dict) else {}
            if isinstance(ta, dict) and not job_fit:
                job_fit = ta.get("job_fit", {})
            multipass = analysis.get("multipass_analysis", {})
            hr_criteria = analysis.get("hr_criteria", {})

            # Scores and matrices
            tech_score = multipass.get("technical", {}).get("technical_score", 0.5) if isinstance(multipass, dict) else 0.5
            cultural_score = multipass.get("overall_scores", {}).get("cultural", 0.5) if isinstance(multipass, dict) else 0.5
            behavioral_score = multipass.get("overall_scores", {}).get("behavioral", 0.5) if isinstance(multipass, dict) else 0.5
            overall_fit = job_fit.get("overall_fit_score", 0.5) if isinstance(job_fit, dict) else 0.5
            comm_norm = (hr_criteria.get("overall_score", 50) / 100.0) if isinstance(hr_criteria, dict) else 0.5
            reqs = job_fit.get("requirements_matrix", []) if isinstance(job_fit, dict) else []

            # Count high-importance issues
            high_issues = 0
            try:
                for r in reqs or []:
                    meets = str(r.get("meets", "")).lower()
                    importance = str(r.get("importance", "medium")).lower()
                    weight = float(r.get("weight", 0.0) or 0.0)
                    is_high = (importance == "high") or (weight > 0.5)
                    if is_high and meets in ("partial", "no"):
                        high_issues += 1
            except Exception:
                high_issues = 0

            recommendations: List[str] = []

            # Technical interview when technical signals are weak/uncertain
            if tech_score < 0.7 or overall_fit < 0.65 or high_issues >= 1:
                recommendations.append("Teknik görüşme")

            # HR/culture interview when cultural/communication is weak
            if cultural_score < 0.65 or comm_norm < 0.6:
                recommendations.append("İnsan kaynakları kültür uyum görüşmesi")

            # Manager interview for team/leadership alignment or when decision is hold
            try:
                ai_opinion = ta.get("ai_opinion", {}) if isinstance(ta, dict) else {}
                decision = ai_opinion.get("hire_recommendation")
            except Exception:
                decision = None
            if (behavioral_score < 0.7) or (decision == "Hold"):
                recommendations.append("Yönetici görüşmesi")

            # Deduplicate while preserving order
            seen = set()
            ordered = []
            for it in recommendations:
                if it not in seen:
                    seen.add(it)
                    ordered.append(it)
            return ordered
        except Exception:
            return []
    


def export_to_markdown(report: Dict[str, Any]) -> str:
    """Export report to markdown format"""
    metadata = report.get("metadata", {})
    content = report.get("content", {})
    scoring = report.get("scoring", {})
    recommendations = report.get("recommendations", {})
    viz = report.get("visualization_data", {})
    
    md = f"""# Interview Report

## Candidate Information
- **Name**: {metadata.get('candidate_name')}
- **Position**: {metadata.get('position')}
- **Interview Date**: {metadata.get('interview_date')}
- **Report Generated**: {metadata.get('report_generated')}

> Not: Bu rapor AI destekli öneriler içerir; nihai işe alım kararı panel onayıyla verilir. Ses/ton metrikleri sadece yardımcı amaçlıdır ve toplam skora doğrudan eklenmez.

## Executive Summary
**Recommendation**: {content.get('executive_overview', {}).get('recommendation', 'N/A')}
**Confidence**: {content.get('executive_overview', {}).get('confidence', 'N/A')}

{content.get('executive_overview', {}).get('key_verdict', '')}

## Competency Scores
"""
    
    for competency, score in scoring.items():
        md += f"- **{competency.replace('_', ' ').title()}**: {score:.2f}\n"
    
    md += "\n## Key Highlights\n"
    
    highlights = content.get('critical_highlights', {})
    if highlights.get('top_strengths'):
        md += "\n### Strengths\n"
        for strength in highlights['top_strengths']:
            md += f"- {strength}\n"
    
    if highlights.get('main_concerns'):
        md += "\n### Concerns\n"
        for concern in highlights['main_concerns']:
            md += f"- {concern}\n"
    
    md += "\n## Recommendations\n"
    for category, items in recommendations.items():
        md += f"\n### {category.replace('_', ' ').title()}\n"
        for item in items:
            md += f"- {item}\n"

    # Panel decision and work samples sections if present
    panel = viz.get('evidence_based', {}).get('panel_review') if isinstance(viz, dict) else None
    ws = viz.get('evidence_based', {}).get('work_samples') if isinstance(viz, dict) else None
    if panel and panel.get('decision'):
        md += "\n## Panel Decision\n"
        md += f"- Decision: {panel.get('decision')}\n"
        if panel.get('notes'):
            md += f"- Notes: {panel.get('notes')}\n"
        if isinstance(panel.get('rubric'), list) and panel['rubric']:
            md += "\n### Panel Rubric\n"
            for r in panel['rubric']:
                md += f"- {r.get('label')}: {r.get('score_0_100')}/100"
                if isinstance(r.get('weight_0_1'), (int, float)):
                    md += f" (weight {(r['weight_0_1']*100):.0f}%)"
                md += "\n"
    if isinstance(ws, list) and ws:
        md += "\n## Work Samples / Tests\n"
        for w in ws:
            md += f"- {w.get('name')}: {w.get('score_0_100')}/100"
            if isinstance(w.get('weight_0_1'), (int, float)):
                md += f" (weight {(w['weight_0_1']*100):.0f}%)"
            if w.get('notes'):
                md += f" – {w.get('notes')}"
            md += "\n"
    
    return md


def export_to_structured_json(report: Dict[str, Any]) -> str:
    """Export report to structured JSON for API consumption"""
    return json.dumps(report, indent=2, ensure_ascii=False)
