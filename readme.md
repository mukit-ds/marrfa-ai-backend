# Marrfa AI Chatbot - Backend API

## 📋 Overview
Marrfa AI Chatbot is a sophisticated real estate assistant that combines property search capabilities with company knowledge retrieval using RAG (Retrieval-Augmented Generation) technology. The system provides natural language interactions for finding properties in Dubai and answering questions about Marrfa Real Estate Company.

## 🏗️ Architecture
The backend is built with **FastAPI** and follows a modular architecture:
- **FastAPI**: Modern Python web framework for building APIs
- **MongoDB**: User authentication and usage tracking
- **FAISS**: Vector database for semantic search
- **OpenAI API**: For embeddings, chat completions, and audio transcription
- **Streamlit**: Frontend interface

## 📁 Project Structure

### Core Application Files:

| File | Purpose | Key Functions |
|------|---------|--------------|
| **`main.py`** | Main FastAPI application entry point | Handles all API endpoints, request routing, and application setup |
| **`app.py`** | Streamlit frontend interface | User interface, chat display, property cards, file uploads |
| **`schemas.py`** | Pydantic data models | Defines request/response structures for API validation |
| **`faiss_kb.py`** | Knowledge Base with FAISS | Vector search, semantic retrieval for company information |

### Specialized Modules:

| File | Purpose | Key Functions |
|------|---------|--------------|
| **`marrfa_client.py`** | Property API client | Fetches properties from Marrfa API, normalizes data |
| **`parser.py`** | Natural language query parser | Extracts filters from text queries (price, location, bedrooms, etc.) |
| **`intent_classifier.py`** | Query intent detection | Classifies queries as PROPERTY/COMPANY/OUT_OF_CONTEXT |
| **`file_processor.py`** | File content extraction | Processes PDF, DOCX, images, CSV files using OCR and text extraction |
| **`audio_transcription.py`** | Voice input processing | Transcribes audio files using OpenAI Whisper |
| **`property_search.py`** | Property search logic | Coordinates property search with filters and results formatting |
| **`company_kb.py`** | Company knowledge handling | Manages company-related queries and responses |
| **`auth.py`** | Authentication utilities | User login/signup, password hashing, session management |
| **`voice_bar.html`** | Custom voice UI component | HTML template for voice recording interface |

## 🚀 Features

### 1. **Intelligent Query Routing**
- Classifies user queries into categories: Property Search, Company Information, or Out-of-Context
- Uses LLM-based intent classification with fallback keyword matching

### 2. **Property Search**
- Natural language property search in Dubai
- Supports filters: price range, location, bedrooms, property type
- Integration with Marrfa API for real-time property data
- Beautiful property card display with images and details

### 3. **Company Knowledge Base**
- FAISS-based vector search for company information
- RAG (Retrieval-Augmented Generation) for accurate responses
- Covers: CEO info, team, policies, terms & conditions, partnerships

### 4. **Multi-Modal Input Support**
- **Text chat**: Standard text-based queries
- **Voice input**: Audio recording with transcription
- **File upload**: PDF, DOCX, images, CSV, TXT file analysis
- **Image OCR**: Text extraction from uploaded images

### 5. **User Management**
- User authentication (login/signup)
- Anonymous usage with 3-query limit
- MongoDB-backed user storage
- Session management

### 6. **Advanced Features**
- Context-aware responses based on query type
- Smart file processing with OpenAI Vision API fallback
- CORS-enabled API for frontend integration
- Health monitoring and debugging endpoints

## 🔧 API Endpoints

### Core Endpoints:
- `POST /api/chat` - Main chat endpoint with file upload support
- `POST /api/transcribe` - Audio transcription
- `POST /api/login` - User authentication
- `POST /api/signup` - User registration
- `GET /health` - System health check
- `GET /api/debug-kb` - Knowledge base debugging

### Request Flow:
1. User sends query via frontend
2. System checks authentication and usage limits
3. Query is classified by intent
4. Based on intent:
   - **PROPERTY**: Parse filters → Search API → Format results
   - **COMPANY**: FAISS search → RAG response generation
   - **FILES**: Process files → AI analysis → Response
5. Structured response returned to frontend

## 🛠️ Setup & Installation

### Prerequisites:
- Python 3.9+
- MongoDB instance
- OpenAI API key
- Marrfa API access

### Environment Variables:
```env
OPENAI_API_KEY=your_openai_api_key
MONGO_URI=your_mongodb_connection_string
```

### Installation:
```bash
# Clone repository
git clone https://github.com/dev-marrfa-discovery/marrfa-ai-backend.git

# Navigate to backend
cd backend/app

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run the backend
uvicorn main:app --reload

# Run the frontend (separate terminal)
streamlit run app.py
```

## 📊 Database Schema

### MongoDB Collections:
1. **users**: User authentication data
   - username, email, password_hash, created_at
2. **anonymous_usage**: Usage tracking for non-logged-in users
   - session_id, query_count, first_seen

### FAISS Knowledge Base:
- Vector embeddings of company documents
- Chunked text with metadata (title, URL, content)
- Cosine similarity search for retrieval

## 🎯 Use Cases

### Real Estate Agents:
- Quick property searches for clients
- Access to company information and policies
- Document analysis for property listings

### Customers:
- Natural language property discovery
- Company information and contact details
- File upload for property document analysis

### Support Team:
- Quick answers to common questions
- Policy and terms reference
- Document processing assistance

## 🔍 Example Queries

### Property Search:
- "Show me 2-bedroom apartments in Dubai Marina under 2M AED"
- "Villas in Dubai Hills with pool"
- "Studio apartments for rent in JVC"

### Company Information:
- "Who is the CEO of Marrfa?"
- "What are your privacy policies?"
- "Tell me about the Marrfa team"

### File Analysis:
- Upload property brochures for summary
- Analyze lease agreements
- Extract text from property images

## 🚀 Deployment

### Local Development:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Production Considerations:
- Use Gunicorn with Uvicorn workers
- Implement Redis for caching
- Add API rate limiting
- Set up proper logging and monitoring
- Configure SSL/TLS encryption

## 📈 Performance

- **Response Time**: < 2 seconds for typical queries
- **File Processing**: Supports up to 10MB files
- **Concurrent Users**: Scales with FastAPI's async capabilities
- **Knowledge Base**: FAISS enables millisecond semantic search

## 🔮 Future Enhancements

1. **Multi-language Support**: Arabic and other language support
2. **Advanced Filtering**: More sophisticated property filters
3. **Conversation Memory**: Context-aware multi-turn conversations
4. **Notification System**: Property alerts and updates
5. **Analytics Dashboard**: Usage insights and query analytics

## 📞 Support

For issues, feature requests, or contributions:
- GitHub Issues: [Project Repository](https://github.com/dev-marrfa-discovery/marrfa-ai-backend)
- Documentation: In-code comments and this README
- Contact: Through GitHub repository

## 📄 License

Proprietary - Marrfa Real Estate Company

---

