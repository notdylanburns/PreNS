const HOSTS = [];
const SEEN_HOSTS = new Set();
const HEIRARCHY = {};
const PARENTS = {};

function submit() {
    const hostname = document.getElementById("hostname_input").value;
    const ttl = parseInt(document.getElementById("ttl_input").value);

    fetch(
        "/api/host",
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
            },
            "body": JSON.stringify({
                "hostname": hostname,
                "ttl": ttl,
            })
        }
    )
    .then(response => response.json())
    .then(data => {
        append_hosts([data]);
        render_table();
    });
}

function change_view(elem) {
    const target_id = `view_${elem.value}`;
    document.querySelectorAll(".view-container").forEach(
        view => view.id === target_id ? view.classList.remove("hidden") : view.classList.add("hidden")
    );
}

async function fetch_hosts() {
    return fetch("/api/hosts").then(response => response.json());
}

async function fetch_children(label_id) {
    return fetch(`/api/label/${label_id}/children`).then(response => response.json());
}

function append_hosts(hosts) {
    const new_hosts = hosts.filter(host => !SEEN_HOSTS.has(host.id));
    HOSTS.push(...new_hosts);
    HOSTS.sort((a, b) => a.hostname.localeCompare(b.hostname));

    new_hosts.forEach(host => SEEN_HOSTS.add(host.id));
}

function append_heirarchy(parent, children) {
    children.sort((a, b) => a.name.localeCompare(b.name));
    parent.children = children;

    for (const child of children) {
        PARENTS[child.id] = child;
    }
}

function delete_hostname(img, id) {
    fetch(
        `/api/host/${id}`,
        {
            "method": "DELETE",
        }
    ).then(() => img.parentNode.parentNode.remove());
}

function render_table() {
    const tbody = document.getElementById("data_table");
    tbody.innerHTML = HOSTS.map(row => `
        <tr>
            <td>${row.hostname}</td>
            <td>${row.ttl}</td>
            <td>${row.resolved_at ?? ""}</td>
            <td>${row.error_message ?? ""}</td>
            <td class="delete-icon"><img src="delete.png" height="30px" onclick="delete_hostname(this, ${row.id})"/></td>
        </tr>
    `).join("");
}

function get_children(elem, id) {
    if (elem.parentNode.open) return false;
    fetch_children(id).then(children => {
        append_heirarchy(PARENTS[id], children);
        elem.parentNode.querySelector("ul").innerHTML = children.map(child => render_level(child)).join("");
    });
}

function render_level(value) {
    let inner = "";
    if (value.hostname_id !== null) {
        const host = HOSTS.find(h => h.id === value.hostname_id);

        if (host) {
            inner = `
                <div>
                    <strong>TTL: </strong>${host.ttl}<br />
                    <strong>Last Resolved At: </strong>${host.resolved_at ?? ""}<br />
                    <strong>Error: </strong>${host.error_message ?? ""}<br />
                </div>
            `;
        }
    };

    return `
        <li>
            <details>
                <summary onclick="get_children(this, ${value.id})">${value.name}</summary>
                ${inner}
                <ul></ul>
            </details>
        </li>
    `
}

function render_list() {
    const container = document.getElementById("data_list");

    container.innerHTML = HEIRARCHY.children.map(render_level).join("");
}

function refresh() {
    fetch_hosts().then(hosts => {
        append_hosts(hosts);
        render_table();
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    append_hosts(await fetch_hosts());
    render_table();

    append_heirarchy(HEIRARCHY, await fetch_children(0));
    render_list();

    const selected_view = document.querySelector("input[type=radio][name=view]:checked");
    if (selected_view !== null) change_view(selected_view);

    document.getElementById("view_loading").classList.add("hidden");
});
