# Security Configuration Guide

## Overview

This guide provides essential security configuration instructions for the Blackcore intelligence processing system. Following these guidelines is **critical** for maintaining the security of your sensitive data.

## Master Key Configuration

### BLACKCORE_MASTER_KEY (Required)

The `BLACKCORE_MASTER_KEY` environment variable is **required** for encrypting sensitive data stored locally. Without this key, the application will not start.

### Generating a Secure Master Key

You have several options for generating a secure master key:

#### Option 1: Using the provided script (Recommended)

```bash
# Generate a high-complexity 32-character key
python scripts/generate_master_key.py

# Generate and save directly to .env file
python scripts/generate_master_key.py --save

# Generate a longer key for extra security
python scripts/generate_master_key.py --length 64
```

#### Option 2: Using Python

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Option 3: Using OpenSSL

```bash
openssl rand -base64 32
```

### Key Requirements

- **Minimum length**: 16 characters (32+ recommended)
- **Character set**: Use a mix of letters, numbers, and special characters
- **Uniqueness**: Generate a different key for each environment (dev, staging, production)

### Setting the Master Key

1. Copy your generated key
2. Add it to your `.env` file:
   ```
   BLACKCORE_MASTER_KEY=your_generated_key_here
   ```
3. Ensure your `.env` file has proper permissions:
   ```bash
   chmod 600 .env
   ```

### Security Best Practices

1. **Never commit the master key** to version control
2. **Store the key securely** in a password manager
3. **Rotate keys periodically** (recommended: every 90 days)
4. **Use different keys** for different environments
5. **Back up your key** securely - losing it means losing access to encrypted data

### Key Rotation

To rotate your master key:

1. Generate a new key using one of the methods above
2. Update the `BLACKCORE_MASTER_KEY` in your environment
3. Restart the application
4. The system will automatically re-encrypt existing secrets with the new key

### Troubleshooting

#### Error: "BLACKCORE_MASTER_KEY environment variable must be set"

This error occurs when the master key is not configured. Generate a key and add it to your `.env` file.

#### Error: "BLACKCORE_MASTER_KEY must be at least 16 characters long"

Your key is too short. Generate a longer key (32+ characters recommended).

## Other Security Configuration

### API Keys

Store all API keys in environment variables:

```bash
# Notion API (Required)
NOTION_API_KEY=your_notion_integration_token

# AI Services (Optional)
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
```

### Redis Configuration (Optional)

For distributed rate limiting:

```bash
REDIS_URL=redis://localhost:6379/0
```

### Security Checklist

- [ ] Generated a secure BLACKCORE_MASTER_KEY (32+ characters)
- [ ] Added master key to `.env` file
- [ ] Set proper file permissions on `.env` (600)
- [ ] Stored master key in password manager
- [ ] Added `.env` to `.gitignore`
- [ ] Configured all API keys as environment variables
- [ ] Reviewed and understood key rotation procedures

## Additional Resources

- [Generate Master Key Script](../scripts/generate_master_key.py)
- [Environment Configuration Example](../.env.example)
- [Security Module Documentation](../blackcore/security/)

---

**Remember**: Security is only as strong as your weakest link. Always follow these guidelines and never take shortcuts with security configuration.