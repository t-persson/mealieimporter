function importer(event) {
    event.preventDefault();
    document.getElementById("messages").innerHTML = "";
    var formData = new FormData(event.target);
    let recipe = formData.get("recipe");
    let api = formData.get("api");
    document.getElementById("import").setAttribute("disabled", true);
    const evtSource = new EventSource(`http://192.168.1.136:8000/api?api=${api}&recipe=${recipe}`);
    evtSource.addEventListener("done", (event) => {
        document.getElementById("importer").reset();
        evtSource.close();
        document.getElementById("import").removeAttribute("disabled");
    });
    evtSource.onmessage = (event) => {
        const newElement = document.createElement("p");
        newElement.appendChild(document.createTextNode(event.data));
        document.getElementById("messages").appendChild(newElement);
    }
}

document.addEventListener("submit", importer);
