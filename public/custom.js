// public/custom.js
window.onload = function() {
    const url = window.location.href;
    const urlParams = new URL(url).searchParams;
    const params = {};
    for (const [key, value] of urlParams.entries()) {
    params[key] = value;
    }

    window.sendChainlitMessage({
    type: "url_params",
    params: params
    });    
};
    

