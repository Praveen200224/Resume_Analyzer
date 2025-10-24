import os
import re
import tempfile
import json
import math
import requests
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect, String, Line
import io
import datetime


class AIResumeAnalyzer:
    def analyze_resume(self, resume_text, job_role=None, role_info=None, model="Google Gemini"):
        """
        Analyze a resume using the specified AI model
        Parameters:
        - resume_text: The text content of the resume
        - job_role: The target job role
        - role_info: Additional information about the job role
        - model: The AI model to use ("Google Gemini" or "Anthropic Claude")
        Returns:
        - Dictionary containing analysis results
        """
        import traceback
        def clean_markdown(text):
            if not text:
                return ""
            import re
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            text = re.sub(r'\*(.*?)\*', r'\1', text)
            text = re.sub(r'__(.*?)__', r'\1', text)
            text = re.sub(r'_(.*?)_', r'\1', text)
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
            return text.strip()
        try:
            # print("[DEBUG] First 500 chars of resume_text:", (resume_text[:500] if resume_text else "<EMPTY>"))
            job_description = None
            if role_info:
                job_description = f"""
                Role: {job_role}
                Description: {role_info.get('description', '')}
                Required Skills: {', '.join(role_info.get('required_skills', []))}
                """
            # Choose the appropriate model for analysis
            if model == "Google Gemini":
                # Use gemini-1.5-flash for best results
                if not self.google_api_key:
                    return {"error": "Google API key is not configured. Please add it to your .env file."}
                try:
                    # Explicitly list available models and use the correct one
                    available_models = [m.name for m in genai.list_models()]
                    if "models/gemini-2.5-flash" in available_models:
                        model_gemini = genai.GenerativeModel("gemini-2.5-flash")
                    elif "models/gemini-2.5-pro" in available_models:
                        model_gemini = genai.GenerativeModel("gemini-2.5-pro")
                    elif "models/gemini-pro-latest" in available_models:
                        model_gemini = genai.GenerativeModel("gemini-pro-latest")
                    elif "models/gemini-1.5-flash" in available_models:
                        model_gemini = genai.GenerativeModel("gemini-1.5-flash")
                    elif "models/gemini-pro" in available_models:
                        model_gemini = genai.GenerativeModel("gemini-pro")
                    else:
                        return {"error": "Gemini model not available in your API key/account. Please check your Google AI Studio access."}
                    base_prompt = f"""
                    You are an expert resume analyst with deep knowledge of industry standards, job requirements, and hiring practices across various fields. Your task is to provide a comprehensive, detailed analysis of the resume provided.
                    Please structure your response in the following format:
                    ## Overall Assessment
                    [Provide a detailed assessment of the resume's overall quality, effectiveness, and alignment with industry standards. Include specific observations about formatting, content organization, and general impression. Be thorough and specific.]
                    ## Professional Profile Analysis
                    [Analyze the candidate's professional profile, experience trajectory, and career narrative. Discuss how well their story comes across and whether their career progression makes sense for their apparent goals.]
                    ## Skills Analysis
                    - **Current Skills**: [List ALL skills the candidate demonstrates in their resume, categorized by type (technical, soft, domain-specific, etc.). Be comprehensive.]
                    - **Skill Proficiency**: [Assess the apparent level of expertise in key skills based on how they're presented in the resume]
                    - **Missing Skills**: [List important skills that would improve the resume for their target role. Be specific and explain why each skill matters.]
                    ## Experience Analysis
                    [Provide detailed feedback on how well the candidate has presented their experience. Analyze the use of action verbs, quantifiable achievements, and relevance to their target role. Suggest specific improvements.]
                    ## Education Analysis
                    [Analyze the education section, including relevance of degrees, certifications, and any missing educational elements that would strengthen their profile.]
                    ## Key Strengths
                    [List 5-7 specific strengths of the resume with detailed explanations of why these are effective]
                    ## Areas for Improvement
                    [List 5-7 specific areas where the resume could be improved with detailed, actionable recommendations]
                    ## ATS Optimization Assessment
                    [Analyze how well the resume is optimized for Applicant Tracking Systems. Provide a specific ATS score from 0-100, with 100 being perfectly optimized. Use this format: "ATS Score: XX/100". Then suggest specific keywords and formatting changes to improve ATS performance.]
                    ## Recommended Courses/Certifications
                    [Suggest 5-7 specific courses or certifications that would enhance the candidate's profile, with a brief explanation of why each would be valuable]
                    ## Resume Score
                    [Provide a score from 0-100 based on the overall quality of the resume. Use this format exactly: "Resume Score: XX/100" where XX is the numerical score. Be consistent with your assessment - a resume with significant issues should score below 60, an average resume 60-75, a good resume 75-85, and an excellent resume 85-100.]
                    Resume:
                    {resume_text}
                    """
                    if job_role:
                        base_prompt += f"""
                        The candidate is targeting a role as: {job_role}
                        ## Role Alignment Analysis
                        [Analyze how well the resume aligns with the target role of {job_role}. Provide specific recommendations to better align the resume with this role.]
                        """
                    if job_description:
                        base_prompt += f"""
                        Additionally, compare this resume to the following job description:
                        Job Description:
                        {job_description}
                        ## Job Match Analysis
                        [Provide a detailed analysis of how well the resume matches the job description, with a match percentage and specific areas of alignment and misalignment]
                        ## Key Job Requirements Not Met
                        [List specific requirements from the job description that are not addressed in the resume, with recommendations on how to address each gap]
                        """
                    response = model_gemini.generate_content(base_prompt)
                    # print("Gemini raw response:", response)
                    if hasattr(response, "text"):
                        # print("Gemini response.text:", response.text)
                        pass
                    analysis = response.text.strip() if hasattr(response, "text") else str(response)
                    model_used = "Google Gemini (gemini-1.5-flash)"
                except Exception as e:
                    # print(f"Gemini API Exception: {e}")
                    return {"error": f"Analysis failed: {str(e)}"}
            elif model == "Anthropic Claude":
                # Placeholder for Anthropic Claude logic
                return {"error": "Anthropic Claude integration not implemented in this version."}
            else:
                return {"error": "Unknown model selected."}
            # Extract strengths
            strengths = []
            if "## Key Strengths" in analysis:
                strengths_section = analysis.split("## Key Strengths")[1].split("##")[0].strip()
                strengths = [clean_markdown(s.strip().replace("- ", "").replace("* ", "").replace("• ", "")) 
                            for s in strengths_section.split("\n") 
                            if s.strip() and (s.strip().startswith("-") or s.strip().startswith("*") or s.strip().startswith("•"))]
            # Extract weaknesses/areas for improvement
            weaknesses = []
            if "## Areas for Improvement" in analysis:
                weaknesses_section = analysis.split("## Areas for Improvement")[1].split("##")[0].strip()
                weaknesses = [clean_markdown(w.strip().replace("- ", "").replace("* ", "").replace("• ", "")) 
                             for w in weaknesses_section.split("\n") 
                             if w.strip() and (w.strip().startswith("-") or w.strip().startswith("*") or w.strip().startswith("•"))]
            # Extract suggestions/recommendations
            suggestions = []
            if "## Recommended Courses" in analysis:
                suggestions_section = analysis.split("## Recommended Courses")[1].split("##")[0].strip()
                suggestions = [clean_markdown(s.strip().replace("- ", "").replace("* ", "").replace("• ", "")) 
                                 for s in suggestions_section.split("\n") 
                                 if s.strip() and (s.strip().startswith("-") or s.strip().startswith("*") or s.strip().startswith("•"))]
            # Extract score
            def extract_score_from_text(analysis_text):
                import re
                if "## Resume Score" in analysis_text:
                    score_section = analysis_text.split("## Resume Score")[1].strip()
                    score_match = re.search(r'Resume Score:\s*(\d{1,3})/100', score_section)
                    if score_match:
                        score = int(score_match.group(1))
                        return max(0, min(score, 100))
                    score_match = re.search(r'\b(\d{1,3})\b', score_section)
                    if score_match:
                        score = int(score_match.group(1))
                        return max(0, min(score, 100))
                score_match = re.search(r'Resume Score:\s*(\d{1,3})/100', analysis_text)
                if score_match:
                    score = int(score_match.group(1))
                    return max(0, min(score, 100))
                return 0
            score = extract_score_from_text(analysis)
            # Extract ATS score
            def extract_ats_score_from_text(analysis_text):
                import re
                if "## ATS Optimization Assessment" in analysis_text:
                    ats_section = analysis_text.split("## ATS Optimization Assessment")[1].split("##")[0].strip()
                    score_match = re.search(r'ATS Score:\s*(\d{1,3})/100', ats_section)
                    if score_match:
                        score = int(score_match.group(1))
                        return max(0, min(score, 100))
                return 0
            ats_score = extract_ats_score_from_text(analysis)
            return {
                "score": score,
                "ats_score": ats_score,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "suggestions": suggestions,
                "full_response": analysis,
                "model_used": model_used
            }
        except Exception as e:
            # print(f"Error in analyze_resume: {str(e)}")
            # print(traceback.format_exc())
            return {
                "error": f"Analysis failed: {str(e)}",
                "score": 0,
                "ats_score": 0,
                "strengths": ["Unable to analyze resume due to an error."],
                "weaknesses": ["Unable to analyze resume due to an error."],
                "suggestions": ["Try again with a different model or check your resume format."],
                "full_response": f"Error: {str(e)}",
                "model_used": "Error"
            }
    def extract_text_from_docx(self, docx_file):
        """Extract text from DOCX file."""
        try:
            from docx import Document
            import tempfile
            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                temp_file.write(docx_file.getbuffer())
                temp_path = temp_file.name
            text = ""
            doc = Document(temp_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
            # print("[DEBUG] First 500 chars of DOCX extracted text:", (text[:500] if text else "<EMPTY>"))
            return text.strip()
        except Exception as e:
            # print(f"[ERROR] DOCX extraction failed: {e}")
            return ""
    def __init__(self):
        # Load environment variables
        load_dotenv()
        # Configure Google Gemini AI
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        # Always set the API key directly for reliability
        if self.google_api_key:
            genai.configure(api_key=self.google_api_key)
        else:
            # Fallback: try to set a hardcoded key if available
            try:
                import secrets
                genai.configure(api_key=secrets.GOOGLE_API_KEY)
            except Exception:
                pass
    
    def extract_text_from_pdf(self, pdf_file):
        """Extract text from PDF using pdfplumber and OCR if needed"""
        text = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            if hasattr(pdf_file, 'getbuffer'):
                temp_file.write(pdf_file.getbuffer())
            elif hasattr(pdf_file, 'read'):
                temp_file.write(pdf_file.read())
                pdf_file.seek(0)
            else:
                temp_file.write(pdf_file)
            temp_path = temp_file.name
        try:
            with pdfplumber.open(temp_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            # print("[DEBUG] First 500 chars of PDF extracted text:", (text[:500] if text else "<EMPTY>"))
            return text.strip()
        except Exception as e:
            # print(f"[ERROR] PDF extraction failed: {e}")
            return ""

    def simple_generate_pdf_report(self, analysis_result, candidate_name, job_role):
        """Generate a simple PDF report with candidate info and analysis summary."""
        import io
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        import datetime

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()

        content = []
        # Title
        content.append(Paragraph("Resume Analysis Report", styles['Title']))
        content.append(Spacer(1, 0.2*inch))

        # Date
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        content.append(Paragraph(f"Generated on: {current_date}", styles['Normal']))
        content.append(Spacer(1, 0.2*inch))

        # Candidate Info
        candidate_display = candidate_name if candidate_name else "Candidate"
        job_role_display = job_role if job_role else "Not specified"
        content.append(Paragraph(f"<b>Candidate:</b> {candidate_display}", styles['Normal']))
        content.append(Paragraph(f"<b>Target Role:</b> {job_role_display}", styles['Normal']))
        content.append(Spacer(1, 0.2*inch))

        # Model Used
        model_used = analysis_result.get("model_used", "AI")
        content.append(Paragraph(f"<b>Analysis Model:</b> {model_used}", styles['Normal']))
        content.append(Spacer(1, 0.2*inch))

        # Resume Score
        resume_score = analysis_result.get("score", analysis_result.get("resume_score", None))
        if resume_score is not None:
            try:
                resume_score = int(resume_score)
                resume_score = max(0, min(resume_score, 100))
                content.append(Paragraph(f"<b>Resume Score:</b> {resume_score}/100", styles['Normal']))
                content.append(Spacer(1, 0.2*inch))
            except Exception:
                pass

        # Executive Summary
        analysis_text = analysis_result.get("full_response", "") or analysis_result.get("analysis", "")
        summary = ""
        if "## Overall Assessment" in analysis_text:
            summary = analysis_text.split("## Overall Assessment")[1].split("##")[0].strip()
        elif analysis_text:
            summary = analysis_text.strip().split("\n")[0]
        if summary:
            content.append(Paragraph("<b>Executive Summary:</b>", styles['Heading2']))
            content.append(Paragraph(summary, styles['Normal']))
            content.append(Spacer(1, 0.2*inch))

        # Key Strengths and Areas for Improvement
        strengths = analysis_result.get("strengths", [])
        weaknesses = analysis_result.get("weaknesses", [])
        if strengths or weaknesses:
            content.append(Paragraph("<b>Key Strengths:</b>", styles['Heading3']))
            for s in strengths:
                content.append(Paragraph(f"• {s}", styles['Normal']))
            content.append(Spacer(1, 0.1*inch))
            content.append(Paragraph("<b>Areas for Improvement:</b>", styles['Heading3']))
            for w in weaknesses:
                content.append(Paragraph(f"• {w}", styles['Normal']))
            content.append(Spacer(1, 0.2*inch))

        # Recommended Courses
        courses = analysis_result.get("suggestions", [])
        if courses:
            content.append(Paragraph("<b>Recommended Courses & Certifications:</b>", styles['Heading3']))
            for course in courses:
                content.append(Paragraph(f"• {course}", styles['Normal']))
            content.append(Spacer(1, 0.2*inch))

        # Footer with page number
        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            page_num = canvas.getPageNumber()
            text = f"Page {page_num}"
            canvas.drawRightString(7.5*inch, 0.5*inch, text)
            canvas.restoreState()

        doc.build(content, onFirstPage=add_page_number, onLaterPages=add_page_number)
        buffer.seek(0)
        return buffer

    def process_sections(self, analysis_text, content, normal_style, list_item_style, subheading_style, heading_style, clean_markdown):
        """Process sections of the analysis text with special handling for certain sections"""
        # Parse the markdown-like content
        sections = analysis_text.split("##")
        
        # Define sections to include in detailed analysis
        detailed_sections = [
            "Professional Profile Analysis",
            "Skills Analysis",
            "Experience Analysis",
            "Education Analysis",
            "ATS Optimization Assessment",
            "Role Alignment Analysis",
            "Job Match Analysis"
        ]
        
        # Add Detailed Analysis section
        content.append(Paragraph("Detailed Analysis", heading_style))
        content.append(Spacer(1, 0.1*inch))
        
        for section in sections:
            if not section.strip():
                continue
            
            # Extract section title and content
            lines = section.strip().split("\n")
            section_title = lines[0].strip()
            
            # Skip sections we don't want in the detailed analysis
            if section_title not in detailed_sections and section_title != "Overall Assessment":
                continue
            
            # Skip Overall Assessment as we've already included it
            if section_title == "Overall Assessment":
                continue
            
            section_content = "\n".join(lines[1:]).strip()
            
            # Add section title
            content.append(Paragraph(section_title, subheading_style))
            content.append(Spacer(1, 0.1*inch))
            
            # Process content based on section
            if section_title == "Skills Analysis":
                # Extract current and missing skills
                current_skills = []
                missing_skills = []
                
                if "Current Skills" in section_content:
                    current_part = section_content.split("Current Skills")[1]
                    if "Missing Skills" in current_part:
                        current_part = current_part.split("Missing Skills")[0]
                    
                    for line in current_part.split("\n"):
                        if line.strip() and ("-" in line or "*" in line or "•" in line):
                            skill = clean_markdown(line.replace("-", "").replace("*", "").replace("•", "").strip())
                            if skill:
                                current_skills.append(skill)
                
                if "Missing Skills" in section_content:
                    missing_part = section_content.split("Missing Skills")[1]
                    for line in missing_part.split("\n"):
                        if line.strip() and ("-" in line or "*" in line or "•" in line):
                            skill = clean_markdown(line.replace("-", "").replace("*", "").replace("•", "").strip())
                            if skill:
                                missing_skills.append(skill)
                
                # Create skills table with better formatting
                if current_skills or missing_skills:
                    # Create paragraphs for each skill to ensure proper wrapping
                    current_skill_paragraphs = [Paragraph(skill, normal_style) for skill in current_skills]
                    missing_skill_paragraphs = [Paragraph(skill, normal_style) for skill in missing_skills]
                    
                    # Make sure both lists have the same length
                    max_len = max(len(current_skill_paragraphs), len(missing_skill_paragraphs))
                    current_skill_paragraphs.extend([Paragraph("", normal_style)] * (max_len - len(current_skill_paragraphs)))
                    missing_skill_paragraphs.extend([Paragraph("", normal_style)] * (max_len - len(missing_skill_paragraphs)))
                    
                    # Create data for the table
                    data = [["Current Skills", "Missing Skills"]]
                    for i in range(max_len):
                        data.append([current_skill_paragraphs[i], missing_skill_paragraphs[i]])
                    
                    # Create the table with fixed column widths
                    table = Table(data, colWidths=[3*inch, 3*inch])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (1, 0), colors.lightgreen),
                        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 10),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ]))
                    
                    content.append(table)
                
                # We no longer need to add skill proficiency outside the table
                # as it's now included in the table itself
            elif section_title == "ATS Optimization Assessment":
                # Special handling for ATS Optimization Assessment
                ats_score_line = ""
                ats_content = []
                
                # Extract ATS score if present
                for line in section_content.split("\n"):
                    if "ATS Score:" in line:
                        ats_score_line = clean_markdown(line)
                    elif line.strip():
                        # Check if it's a list item
                        if line.strip().startswith("-") or line.strip().startswith("*") or line.strip().startswith("•"):
                            ats_content.append("• " + clean_markdown(line.strip()[1:].strip()))
                        else:
                            ats_content.append(clean_markdown(line))
                
                # Add ATS score line if found
                if ats_score_line:
                    content.append(Paragraph(ats_score_line, normal_style))
                    content.append(Spacer(1, 0.1*inch))
                
                # Add the rest of the ATS content
                for para in ats_content:
                    if para.startswith("• "):
                        content.append(Paragraph(para, list_item_style))
                    else:
                        content.append(Paragraph(para, normal_style))
            else:
                # Process regular paragraphs
                paragraphs = section_content.split("\n")
                for para in paragraphs:
                    if para.strip():
                        # Check if it's a list item
                        if para.strip().startswith("-") or para.strip().startswith("*") or para.strip().startswith("•"):
                            para = "• " + clean_markdown(para.strip()[1:].strip())
                            content.append(Paragraph(para, list_item_style))
                        else:
                            content.append(Paragraph(clean_markdown(para), normal_style))
            
            content.append(Spacer(1, 0.2*inch))
        
        return content