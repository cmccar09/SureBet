# Git & AWS Amplify Deployment Guide

## Git Setup (Complete ✅)

Your repository is initialized with:
- ✅ `.gitignore` - Protects secrets and credentials
- ✅ `README.md` - Complete documentation
- ✅ `amplify.yml` - Amplify build config
- ✅ `betfair-creds.json.example` - Template for credentials

## Next Steps

### 1. Configure Git User (If Needed)

```powershell
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 2. Commit Everything

```powershell
git add .
git commit -m "Initial commit: AI betting system with self-learning"
```

### 3. Create GitHub Repository

**Option A: Via GitHub Website**
1. Go to https://github.com/new
2. Create new repository (e.g., "ai-betting-system")
3. Don't initialize with README (you already have one)

**Option B: Via GitHub CLI**
```powershell
gh repo create ai-betting-system --private --source=. --remote=origin --push
```

### 4. Push to GitHub

```powershell
git remote add origin https://github.com/YOUR_USERNAME/ai-betting-system.git
git branch -M main
git push -u origin main
```

## AWS Amplify Deployment

### Option 1: Deploy via AWS Console (Recommended)

1. **Go to AWS Amplify Console**
   - https://console.aws.amazon.com/amplify/

2. **Connect Repository**
   - Click "Host web app"
   - Select "GitHub" as your Git provider
   - Authorize AWS Amplify to access your GitHub
   - Select your repository and branch (main)

3. **Configure Build Settings**
   - Amplify will auto-detect `amplify.yml`
   - Build settings are already configured for React frontend
   - Click "Save and Deploy"

4. **Set Environment Variables** (in Amplify Console)
   ```
   ANTHROPIC_API_KEY = your-key-here
   ```

5. **Deploy**
   - Amplify will build and deploy automatically
   - You'll get a URL like: `https://main.d1234567890abc.amplifyapp.com`

### Option 2: Deploy via Amplify CLI

```powershell
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Configure Amplify
amplify configure

# Initialize Amplify in project
cd C:\Users\charl\OneDrive\futuregenAI\Betting\frontend
amplify init

# Add hosting
amplify add hosting

# Publish
amplify publish
```

## Important Notes

### ⚠️ Backend Services

The Amplify deployment only hosts the **React frontend**. You still need:

1. **DynamoDB Table** - Already exists (SureBetBets)
2. **API Server** - Options:
   - **Option A:** Keep running locally (`api_server.py`)
   - **Option B:** Deploy as Lambda + API Gateway
   - **Option C:** Deploy to EC2/ECS

3. **Scheduled Tasks** - Options:
   - **Option A:** Keep Windows Task Scheduler locally
   - **Option B:** Use AWS EventBridge + Lambda

### Frontend Configuration

Update `frontend/src/App.js` API endpoint for production:

```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';
```

Then set in Amplify Console:
```
REACT_APP_API_URL = https://your-api-gateway-url.com/api
```

## Recommended Production Architecture

```
┌─────────────────┐
│   AWS Amplify   │ ← React Frontend (Static Hosting)
│   (Frontend)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Gateway +  │ ← API Server (Lambda)
│     Lambda      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    DynamoDB     │ ← Data Storage
│  (SureBetBets)  │
└─────────────────┘
         ▲
         │
┌─────────────────┐
│  EventBridge    │ ← Scheduled Workflow
│   + Lambda      │   (Every 2 hours)
└─────────────────┘
```

## Deploy API as Lambda (Optional)

```powershell
# Package API server
cd C:\Users\charl\OneDrive\futuregenAI\Betting
pip install -t lambda-api-package/ flask flask-cors boto3
cp api_server.py lambda-api-package/
cd lambda-api-package
zip -r ../api-lambda.zip .

# Deploy to AWS
aws lambda create-function `
  --function-name BettingAPI `
  --runtime python3.9 `
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role `
  --handler api_server.app `
  --zip-file fileb://../api-lambda.zip
```

## Cost Estimate

- **Amplify Hosting**: $0.01/GB served + $0.15/build minute
- **DynamoDB**: On-demand pricing (~$0.25/million requests)
- **Lambda**: Free tier (1M requests/month)
- **API Gateway**: $3.50/million requests

**Estimated Monthly Cost**: $5-20 depending on usage

## Git Commands Reference

```powershell
# View status
git status

# View commit history
git log --oneline

# Create new branch
git checkout -b feature-name

# Push to GitHub
git push origin main

# Pull latest changes
git pull origin main
```

## Support

Repository: https://github.com/YOUR_USERNAME/ai-betting-system
Documentation: See `README.md` in repository
