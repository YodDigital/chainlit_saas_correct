window.getCookiesAndSend = () => {
  const cookies = document.cookie.split('; ').reduce((acc, cookie) => {
    const [key, value] = cookie.split('=').map(decodeURIComponent);
    acc[key] = value;
    return acc;
  }, {});

  window.chainlit.sendMessage({
    type: 'system_message',
    content: 'Cookies: ' + JSON.stringify(cookies),
  });
};

