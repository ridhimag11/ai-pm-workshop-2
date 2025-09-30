# Excuse Email Draft Tool

A complete web application that generates professional excuse emails using Databricks Model Serving LLM. Built with FastAPI backend and React frontend, designed to work locally and deploy seamlessly to Databricks Apps.

## Features

- **Modern UI**: Clean, responsive design with Tailwind CSS
- **Smart Email Generation**: Context-aware excuse emails based on category, tone, and seriousness
- **Multiple Categories**: Running Late, Missed Meeting, Deadline, WFH/OOO, Social, Travel
- **Tone Options**: Sincere, Playful, Corporate
- **Seriousness Levels**: 1 (very silly) to 5 (serious)
- **Copy to Clipboard**: Easy email copying functionality
- **Real-time Validation**: Form validation with helpful error messages
- **Loading States**: Visual feedback during API calls
- **Error Handling**: Comprehensive error handling and user feedback

## Project Structure

```
excuse-gen-app/
├── app.yaml                    # Databricks Apps configuration
├── requirements.txt            # Python dependencies
├── env.example                # Environment variables template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── src/
│   └── app.py                 # FastAPI backend entry point
└── public/
    └── index.html             # Single-page React + Tailwind CSS frontend
```

## Quick Start

### Local Development

1. **Clone and Setup**:
   ```bash
   cd excuse-gen-app
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp env.example .env
   # Edit .env with your Databricks credentials
   ```

3. **Run the Application**:
   ```bash
   python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access the App**:
   Open your browser to `http://localhost:8000`

### Databricks Apps Deployment

1. **Prerequisites**:
   - Databricks workspace with Apps enabled
   - Databricks Model Serving endpoint accessible
   - App secret configured with key `databricks_token`

2. **Deploy**:
   ```bash
   databricks apps deploy excuse-gen-app --source-code-path /path/to/excuse-gen-app
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABRICKS_API_TOKEN` | Your Databricks personal access token | Yes |
| `DATABRICKS_ENDPOINT_URL` | Databricks Model Serving endpoint URL | Yes |
| `PORT` | Server port (default: 8000) | No |
| `HOST` | Server host (default: 0.0.0.0) | No |

### Databricks Apps Configuration

The `app.yaml` file configures the Databricks Apps deployment:

```yaml
command: [
  "uvicorn",
  "src.app:app",
  "--host", "0.0.0.0",
  "--port", "8000"
]

env:
  - name: 'DATABRICKS_API_TOKEN'
    valueFrom: databricks_token  # References App secret
  - name: 'DATABRICKS_ENDPOINT_URL'
    value: "https://dbc-32cf6ae7-cf82.staging.cloud.databricks.com/serving-endpoints/databricks-gpt-oss-120b/invocations"
  - name: 'PORT'
    value: "8000"
  - name: 'HOST'
    value: "0.0.0.0"
```

## API Endpoints

### Main Endpoints

- `POST /api/generate-excuse` - Generate excuse email
- `GET /` - Serve React frontend
- `GET /health` - Health check
- `GET /debug` - Environment debugging

### Monitoring Endpoints

- `GET /healthz` - Kubernetes-style health check
- `GET /ready` - Readiness check
- `GET /ping` - Simple ping
- `GET /metrics` - Prometheus-style metrics

## Usage

### Generating Excuse Emails

1. **Select Category**: Choose from Running Late, Missed Meeting, Deadline, WFH/OOO, Social, or Travel
2. **Choose Tone**: Select Sincere, Playful, or Corporate
3. **Set Seriousness**: Use the slider from 1 (very silly) to 5 (serious)
4. **Fill Details**: Enter recipient name, sender name, and ETA/when information
5. **Generate**: Click "Generate Email" to create your excuse
6. **Copy**: Use "Copy to Clipboard" to copy the generated email

### Request Format

```json
{
  "category": "Running Late",
  "tone": "Playful",
  "seriousness": 3,
  "recipient_name": "Alex",
  "sender_name": "Mona",
  "eta_when": "15 minutes"
}
```

### Response Format

```json
{
  "subject": "Running Late - ETA 15 minutes",
  "body": "Dear Alex,\n\nI wanted to let you know...\n\nBest regards,\nMona",
  "success": true,
  "error": null
}
```

## Technical Details

### Backend (FastAPI)

- **Framework**: FastAPI with CORS middleware
- **LLM Integration**: HTTP calls to Databricks Model Serving
- **Error Handling**: Comprehensive error handling with meaningful messages
- **Logging**: Request/response logging for debugging
- **Static Serving**: Robust file path resolution for different environments

### Frontend (React)

- **Framework**: React 18 with hooks
- **Styling**: Tailwind CSS via CDN
- **State Management**: React hooks for form and UI state
- **API Integration**: Fetch API for backend communication
- **Responsive Design**: Mobile-first design with responsive grid layout

### LLM Integration

- **Prompt Engineering**: Structured prompts for consistent JSON responses
- **Response Parsing**: Multiple format support (OpenAI-style, Databricks-style)
- **Fallback Handling**: Text-based fallback when JSON parsing fails
- **Error Recovery**: Graceful handling of LLM service errors

## Development

### Local Testing

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export DATABRICKS_API_TOKEN="your_token_here"
   export DATABRICKS_ENDPOINT_URL="your_endpoint_url_here"
   ```

3. **Run with Hot Reload**:
   ```bash
   python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
   ```

### Debugging

- **Environment Info**: Visit `/debug` endpoint for environment details
- **Health Checks**: Use `/health`, `/healthz`, `/ready`, `/ping` for monitoring
- **Logs**: Check console output for request/response logging

## Troubleshooting

### Common Issues

1. **Frontend Not Loading**:
   - Check if `public/index.html` exists
   - Verify file permissions
   - Check `/debug` endpoint for path information

2. **LLM Service Errors**:
   - Verify `DATABRICKS_API_TOKEN` is set correctly
   - Check `DATABRICKS_ENDPOINT_URL` is accessible
   - Review error messages in browser console

3. **Deployment Issues**:
   - Ensure port 8000 is used (not 8080)
   - Verify `app.yaml` configuration
   - Check Databricks Apps secret configuration

### Error Messages

- **"DATABRICKS_API_TOKEN not configured"**: Set the environment variable
- **"Request timeout"**: LLM service is slow or unavailable
- **"LLM service error"**: Check endpoint URL and token
- **"Frontend not found"**: Verify `public/index.html` exists

## Security

- **Secrets Management**: Use `valueFrom` in Databricks Apps for sensitive data
- **CORS**: Configured for development; restrict in production
- **Input Validation**: Pydantic models validate all inputs
- **Error Handling**: No sensitive information in error messages

## Performance

- **Async Operations**: Non-blocking HTTP calls to LLM service
- **Efficient Rendering**: React hooks for optimal re-rendering
- **CDN Resources**: React and Tailwind CSS loaded from CDN
- **Minimal Dependencies**: Lightweight Python dependencies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally and on Databricks Apps
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the `/debug` endpoint output
3. Check Databricks Apps logs
4. Open an issue with detailed error information
