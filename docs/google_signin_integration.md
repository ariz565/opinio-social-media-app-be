"""
Google Sign-In Frontend Integration Guide

1. For Web Frontend (HTML/JavaScript):

Add this to your HTML head:

<script src="https://accounts.google.com/gsi/client" async defer></script>

Add this button to your login page:

<div id="g_id_onload"
     data-client_id="YOUR_GOOGLE_CLIENT_ID"
     data-context="signin"
     data-ux_mode="popup"
     data-callback="handleCredentialResponse"
     data-auto_prompt="false">
</div>

<div class="g_id_signin"
     data-type="standard"
     data-shape="rectangular"
     data-theme="outline"
     data-text="signin_with"
     data-size="large"
     data-logo_alignment="left">
</div>

JavaScript handler:
function handleCredentialResponse(response) {
// Send the credential to your backend
fetch('/api/v1/auth/google/token', {
method: 'POST',
headers: {
'Content-Type': 'application/json',
},
body: JSON.stringify({
credential: response.credential
})
})
.then(response => response.json())
.then(data => {
if (data.access_token) {
// Store tokens and redirect
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
window.location.href = '/dashboard';
}
})
.catch(error => {
console.error('Error:', error);
});
}

2. For React/Next.js Frontend:

Install: npm install @google-cloud/local-auth googleapis

Example React component:
import { GoogleLogin } from '@react-oauth/google';

function LoginPage() {
const handleGoogleSuccess = async (credentialResponse) => {
try {
const response = await fetch('/api/v1/auth/google/token', {
method: 'POST',
headers: {
'Content-Type': 'application/json',
},
body: JSON.stringify({
credential: credentialResponse.credential
})
});

            const data = await response.json();

            if (data.access_token) {
                // Store tokens
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                // Redirect to dashboard
                router.push('/dashboard');
            }
        } catch (error) {
            console.error('Google login error:', error);
        }
    };

    return (
        <div>
            <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => {
                    console.log('Login Failed');
                }}
                useOneTap
            />
        </div>
    );

}

3. Environment Variables to Set:

For development, add to your .env file:
GOOGLE_CLIENT_ID=your-actual-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

For production:
GOOGLE_CLIENT_ID=your-production-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-production-google-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback

4. Google Cloud Console Setup:

1. Go to https://console.cloud.google.com/
1. Create a new project or select existing
1. Enable Google+ API
1. Go to Credentials > Create Credentials > OAuth 2.0 Client IDs
1. Set application type to "Web application"
1. Add authorized redirect URIs:
   - http://localhost:8000/api/v1/auth/google/callback (development)
   - https://your-domain.com/api/v1/auth/google/callback (production)
1. Add authorized JavaScript origins:

   - http://localhost:3000 (development)
   - https://your-domain.com (production)

1. API Endpoints Available:

- GET /api/v1/auth/google/login - Get Google auth URL for redirect flow
- POST /api/v1/auth/google/callback - Handle OAuth callback (for redirect flow)
- POST /api/v1/auth/google/token - Direct token authentication (recommended for frontend)

Example curl request:
curl -X POST "http://localhost:8000/api/v1/auth/google/token" \
 -H "Content-Type: application/json" \
 -d '{"access_token": "your-google-access-token"}'

Response:
{
"message": "Google token authentication successful",
"user": {
"\_id": "user_id",
"email": "user@example.com",
"full_name": "User Name",
"username": "username",
"profile_picture": "https://...",
"email_verified": true,
"auth_provider": "google"
},
"access_token": "jwt_access_token",
"refresh_token": "jwt_refresh_token",
"token_type": "bearer",
"expires_in": 1800
}
"""
