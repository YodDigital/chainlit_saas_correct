window.getCookiesAndSend = () => {
  const cookies = document.cookie.split('; ').reduce((acc, cookie) => {
    const [key, value] = cookie.split('=').map(decodeURIComponent);
    acc[key] = value;
    return acc;
  }, {});

  window.chainlit.sendMessage(JSON.stringify(cookies));
};

// Call getCookiesAndSend after the Chainlit UI is ready (with a delay)
setTimeout(window.getCookiesAndSend, 1000);
