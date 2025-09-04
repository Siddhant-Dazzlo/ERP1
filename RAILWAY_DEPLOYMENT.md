# Railway Deployment Guide

This guide will help you deploy your SaaS ERP application to Railway.

## Prerequisites

1. A Railway account (sign up at [railway.app](https://railway.app))
2. Your application code in a Git repository (GitHub, GitLab, or Bitbucket)

## Step 1: Prepare Your Repository

1. Make sure all the Railway configuration files are in your repository:
   - `railway.json`
   - `Procfile`
   - `nixpacks.toml`
   - `requirements.txt`
   - `railway.env.example`

2. Commit and push your changes to your Git repository.

## Step 2: Create a New Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo" (or your preferred Git provider)
4. Choose your repository
5. Railway will automatically detect it's a Python application

## Step 3: Add Required Services

### PostgreSQL Database
1. In your Railway project dashboard, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a PostgreSQL database
4. Note the connection details (you'll need these for environment variables)

### Redis (Optional but Recommended)
1. Click "New" → "Database" → "Redis"
2. Railway will create a Redis instance for caching and Celery

## Step 4: Configure Environment Variables

1. Go to your service settings in Railway
2. Click on "Variables" tab
3. Add the following environment variables:

### Required Variables:
```
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here-change-this
DATABASE_URL=postgresql://username:password@host:port/database
REDIS_URL=redis://username:password@host:port
```

### Optional Variables (for full functionality):
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
STRIPE_SECRET_KEY=sk_test_your_stripe_secret
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret

SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
RATELIMIT_STORAGE_URL=redis://username:password@host:port
```

## Step 5: Deploy

1. Railway will automatically start building and deploying your application
2. You can monitor the build logs in the Railway dashboard
3. Once deployed, Railway will provide you with a public URL

## Step 6: Initialize Database

1. After deployment, your application will automatically run `python init_db.py`
2. This creates the database tables and a default admin user
3. Default admin credentials:
   - Email: `admin@democompany.com`
   - Password: `admin123`

## Step 7: Access Your Application

1. Use the Railway-provided URL to access your application
2. Log in with the default admin credentials
3. Change the default password immediately
4. Create your company and users

## Troubleshooting

### Common Issues:

1. **Build Fails**: Check the build logs in Railway dashboard
2. **Database Connection Error**: Verify DATABASE_URL is correct
3. **Redis Connection Error**: Verify REDIS_URL is correct
4. **Application Crashes**: Check the deployment logs

### Logs:
- View build logs: Railway Dashboard → Your Service → Deployments
- View runtime logs: Railway Dashboard → Your Service → Logs

## Custom Domain (Optional)

1. Go to your service settings
2. Click "Settings" → "Domains"
3. Add your custom domain
4. Update your DNS records as instructed by Railway

## Scaling

Railway automatically handles scaling, but you can:
1. Upgrade your plan for more resources
2. Add multiple services for load balancing
3. Configure auto-scaling based on traffic

## Security Notes

1. Always use strong SECRET_KEY in production
2. Enable HTTPS (Railway provides this automatically)
3. Keep your environment variables secure
4. Regularly update dependencies
5. Monitor your application logs

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Railway Status: [status.railway.app](https://status.railway.app)
