import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const headers = new Headers();
    headers.set('Content-Type', 'application/x-www-form-urlencoded');

    // Use Docker service name instead of localhost
    const backendUrl = process.env.NEXT_PUBLIC_API_URL ? process.env.NEXT_PUBLIC_API_URL : (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');
    const apiPrefix = backendUrl ? `${backendUrl}/api/v1` : '/api/v1';
    const response = await fetch(`${apiPrefix}/auth/login/access-token`, {
      method: 'POST',
      headers: headers,
      body: new URLSearchParams({
        username: body.username,
        password: body.password,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      // Try to parse as JSON, but fall back to plain text if it fails
      let errorDetail;
      try {
        errorDetail = JSON.parse(errorText).detail;
      } catch (e) {
        errorDetail = errorText;
      }
      return NextResponse.json(
        { detail: errorDetail || 'Login failed' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Login proxy error:', error);
    return NextResponse.json(
      { detail: 'An unexpected error occurred.' },
      { status: 500 }
    );
  }
} 