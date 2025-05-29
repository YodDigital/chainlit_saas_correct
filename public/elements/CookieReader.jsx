import React, { useEffect } from 'react';
import { useRecoilValue } from '@chainlit/react-client';
import { sessionIdState } from '@chainlit/react-client';

export default function CookieReader() {
  const sessionId = useRecoilValue(sessionIdState);

  useEffect(() => {
    const cookies = document.cookie.split('; ').reduce((acc, cookie) => {
      const [key, value] = cookie.split('=').map(decodeURIComponent);
      acc[key] = value;
      return acc;
    }, {});

    // Send the cookies to the backend
    sendCookies(cookies);
  }, []);

  const sendCookies = async (cookies) => {
    try {
      const response = await fetch('/.chainlit/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'system_message',
          content: JSON.stringify(cookies),
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        console.error('Failed to send cookies to backend');
      }
    } catch (error) {
      console.error('Error sending cookies:', error);
    }
  };

  return (
    <div>
      {/* This component doesn't render anything */}
    </div>  );
}

