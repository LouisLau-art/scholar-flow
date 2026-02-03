# 🎓 ScholarFlow

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Backend Status](https://img.shields.io/badge/Backend-Hugging%20Face-FFD21E?logo=huggingface)](https://huggingface.co/spaces/LouisShawn/scholarflow-api)
[![Frontend Status](https://img.shields.io/badge/Frontend-Vercel-000000?logo=vercel)](https://scholarflow.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)

**A Modern, AI-Powered Academic Publishing Workflow System**
<br/>
*Streamlining the submission, review, and publication process for the open science era.*

[Live Demo](https://scholarflow.vercel.app) · [Report Bug](https://github.com/LouisLau-art/scholar-flow/issues) · [Request Feature](https://github.com/LouisLau-art/scholar-flow/issues)

</div>

---

## 📖 Introduction

**ScholarFlow** is an open-source editorial management system designed to modernize the academic publishing lifecycle. It replaces legacy, clunky interfaces with a sleek, responsive UI and integrates local AI capabilities to assist editors in matchmaking and quality control.

Built with a "Glue Coding" philosophy, it leverages best-in-class open source components to deliver a robust enterprise-grade solution.

## ✨ Key Features

- **🤖 AI-Assisted Matchmaking**: Local TF-IDF & Semantic Search (via `sentence-transformers`) to recommend the best reviewers without sending data to third-party APIs.
- **📝 Modern Submission Portal**: Drag-and-drop PDF parsing, auto-extraction of metadata, and real-time validation.
- **🔄 Dynamic Editorial Workflow**: 
  - Status Machine: `Submitted` -> `Under Review` -> `Revision` -> `Decision`.
  - Financial Gate: Integrated invoicing and payment tracking before publication.
- **🔒 Secure & Scalable**:
  - **Auth**: Enterprise-ready authentication via Supabase (JWT).
  - **RBAC**: Strict Role-Based Access Control (Author, Reviewer, Editor, Admin).
- **📊 Analytics Dashboard**: Real-time insights into submission rates, acceptance ratios, and turnaround times.

## 🛠️ Tech Stack

### Frontend (User Interface)
- **Framework**: [Next.js 14](https://nextjs.org/) (App Router, TypeScript)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + [Shadcn UI](https://ui.shadcn.com/)
- **State Management**: React Hooks + Server Actions
- **Deployment**: Vercel

### Backend (API & Logic)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.14)
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
- **AI/ML Engine**: 
  - `sentence-transformers` (Local Inference)
  - `scikit-learn` (TF-IDF)
  - `pyroaring` (High-performance bitmap indexing)
- **Deployment**: Hugging Face Spaces (Docker Container)

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 20+
- Docker (Optional, for local containerization)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/LouisLau-art/scholar-flow.git
   cd scholar-flow
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Set up .env
   cp .env.example .env
   # (Fill in your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)
   
   uvicorn main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   
   # Set up .env.local
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   
   npm run dev
   ```

## 🐳 Deployment Architecture

The system uses a **Hybrid Cloud Deployment** strategy to optimize for cost and performance:

1.  **Frontend**: Deployed on **Vercel** (Global Edge Network) for lightning-fast UI delivery.
2.  **Backend**: Deployed on **Hugging Face Spaces** (Docker) to leverage free compute for AI models (`sentence-transformers`) that require significant memory and system libraries (like `gcc` for `pyroaring`).
3.  **Database**: Hosted on **Supabase** (Managed PostgreSQL) for reliability and real-time capabilities.

## 🤝 Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.