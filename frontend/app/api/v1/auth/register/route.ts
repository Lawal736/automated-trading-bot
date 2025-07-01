import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const headers = new Headers(request.headers);
    headers.set('Content-Type', 'application/json');

    // Forward the request to the backend
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/register`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || 'Registration failed' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Registration proxy error:', error);
    return NextResponse.json(
      { detail: 'An unexpected error occurred.' },
      { status: 500 }
    );
  }
} 