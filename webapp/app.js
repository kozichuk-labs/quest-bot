let tg = window.Telegram.WebApp;
tg.expand();

let allUsers = [];
let selectedUser = null;

// Generate deterministic gradient background based on string
function getGradient(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue1 = hash % 360;
    const hue2 = (hash + 40) % 360;
    return `linear-gradient(135deg, hsl(${hue1}, 80%, 60%), hsl(${hue2}, 80%, 50%))`;
}

function getInitials(name) {
    if (!name) return '?';
    return name.substring(0, 2).toUpperCase();
}

async function fetchUsers() {
    try {
        const response = await fetch('/api/users');
        allUsers = await response.json();
        document.getElementById('totalUsers').textContent = allUsers.length;
        renderUsers(allUsers);
    } catch (e) {
        console.error("Failed to fetch users", e);
        document.getElementById('usersList').innerHTML = '<div class="loading">Failed to load users. Are you running local server?</div>';
    }
}

function renderUsers(users) {
    const list = document.getElementById('usersList');
    list.innerHTML = '';
    
    if (users.length === 0) {
        list.innerHTML = '<div class="loading">No users found</div>';
        return;
    }
    
    users.forEach(user => {
        const displayName = user.name || user.username || 'Unknown';
        const displayUsername = user.username ? `@${user.username}` : user.tg_id;
        
        const card = document.createElement('div');
        card.className = 'user-card glass-panel';
        card.onclick = () => openModal(user);
        
        const avatar = document.createElement('div');
        avatar.className = 'user-avatar';
        avatar.style.background = getGradient(displayName + user.tg_id);
        avatar.textContent = getInitials(displayName);
        
        const info = document.createElement('div');
        info.className = 'user-info';
        
        const nameEl = document.createElement('div');
        nameEl.className = 'user-name';
        nameEl.textContent = displayName;
        
        const usernameEl = document.createElement('div');
        usernameEl.className = 'user-username';
        usernameEl.textContent = displayUsername;
        
        const stateEl = document.createElement('div');
        stateEl.className = 'user-state';
        stateEl.textContent = user.current_state;
        
        info.appendChild(nameEl);
        info.appendChild(usernameEl);
        info.appendChild(stateEl);
        
        card.appendChild(avatar);
        card.appendChild(info);
        
        list.appendChild(card);
    });
}

// Search
document.getElementById('searchInput').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    const filtered = allUsers.filter(u => {
        const n = (u.name || '').toLowerCase();
        const un = (u.username || '').toLowerCase();
        return n.includes(q) || un.includes(q) || String(u.tg_id).includes(q);
    });
    renderUsers(filtered);
});

// Modal Logic
function openModal(user) {
    selectedUser = user;
    const displayName = user.name || user.username || 'Unknown';
    
    const avatar = document.getElementById('modalAvatar');
    avatar.style.background = getGradient(displayName + user.tg_id);
    avatar.textContent = getInitials(displayName);
    
    document.getElementById('modalName').textContent = displayName;
    document.getElementById('modalId').textContent = `ID: ${user.tg_id}`;
    document.getElementById('modalState').textContent = user.current_state;
    document.getElementById('modalPasses').textContent = user.pass_count || 0;
    document.getElementById('modalRealName').textContent = user.name || 'Не вказано';
    document.getElementById('modalAge').textContent = user.age || 'Не вказано';
    
    const btnProfile = document.getElementById('btnProfile');
    if (user.username) {
        btnProfile.href = `https://t.me/${user.username}`;
    } else {
        btnProfile.href = `tg://user?id=${user.tg_id}`;
    }
    
    document.getElementById('messageInput').value = '';
    
    document.getElementById('actionModal').classList.remove('hidden');
}

document.getElementById('btnCloseModal').addEventListener('click', () => {
    document.getElementById('actionModal').classList.add('hidden');
    selectedUser = null;
});

// Click outside modal to close
document.getElementById('actionModal').addEventListener('click', (e) => {
    if (e.target.id === 'actionModal') {
        document.getElementById('actionModal').classList.add('hidden');
        selectedUser = null;
    }
});

// Actions
document.getElementById('btnReset').addEventListener('click', async () => {
    if (!selectedUser) return;
    if (confirm(`Reset progress for ${selectedUser.name || selectedUser.username}?`)) {
        try {
            await fetch(`/api/users/${selectedUser.tg_id}/reset`, { method: 'POST' });
            tg.showAlert('Progress reset to WaitQuest1');
            document.getElementById('actionModal').classList.add('hidden');
            fetchUsers();
        } catch (e) {
            tg.showAlert('Error resetting progress');
        }
    }
});

document.getElementById('btnSendMessage').addEventListener('click', async () => {
    if (!selectedUser) return;
    const text = document.getElementById('messageInput').value.trim();
    if (!text) {
        tg.showAlert('Please enter a message');
        return;
    }
    
    try {
        const res = await fetch(`/api/users/${selectedUser.tg_id}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        
        if (res.ok) {
            tg.showAlert('Message sent successfully!');
            document.getElementById('messageInput').value = '';
        } else {
            tg.showAlert('Failed to send message');
        }
    } catch (e) {
        tg.showAlert('Error sending message');
    }
});

// Init
fetchUsers();
