async function apiRequest(url, options) {
    try {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        };

        const response = await fetch(url, options);

        if (response.ok) {
            return await response.json();
        }

        if (response.status === 401) {
            const refreshResult = await refreshToken();

            if (refreshResult.success) {
                return apiRequest(url, options);
            } else {
                redirectToLogin();
            }
        }

        throw new Error(`Request failed with status ${response.status}`);
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

async function refreshToken() {
    try {
        const refreshToken = localStorage.getItem('refreshToken');

        if (!refreshToken) {
            return { success: false };
        }

        const response = await fetch('http://localhost:8000/api/v1/accounts/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('accessToken', data.access);
            return { success: true };
        }

        return { success: false };
    } catch (error) {
        console.error('Token refresh failed:', error);
        return { success: false };
    }
}

function redirectToLogin() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');

    window.location.href = '/login';
}
