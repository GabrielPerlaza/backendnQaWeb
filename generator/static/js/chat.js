function typeWriter(element, text, speed = 20) {
    element.innerHTML = "";
    let i = 0;

    function typing() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(typing, speed);
        }
    }

    typing();
}

fetch("/chat/send/", {
    method: "POST",
    headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/json"
    },
    body: JSON.stringify({ message: userMessage })
})
.then(res => res.json())
.then(data => {
    const aiBubble = document.createElement("div");
    aiBubble.className = "bg-slate-700 p-4 rounded-xl max-w-[75%]";
    chatContainer.appendChild(aiBubble);

    typeWriter(aiBubble, data.response);
});


fetch("/chat/26/", {
  method: "POST",
  headers: {
    "X-CSRFToken": csrftoken,
    "Content-Type": "application/x-www-form-urlencoded"
  },
  body: new URLSearchParams({ message })
})
.then(res => res.json())
.then(data => {
  // pintar mensaje sin reload
})
