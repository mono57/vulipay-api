async function apiRequest(url, options) {
    try {
        // Add the access token to the request
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        };

        // Make the request
        const response = await fetch(url, options);

        // If the request was successful, return the response
        if (response.ok) {
            return await response.json();
        }

        // If the token has expired, try to refresh it
        if (response.status === 401) {
            const refreshResult = await refreshToken();

            // If the refresh was successful, retry the original request
            if (refreshResult.success) {
                return apiRequest(url, options);
            } else {
                // If the refresh failed, redirect to login
                redirectToLogin();
            }
        }

        // Handle other errors
        throw new Error(`Request failed with status ${response.status}`);
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

async function refreshToken() {
    try {
        const refreshToken = localStorage.getItem('refreshToken');

        // If there's no refresh token, we can't refresh
        if (!refreshToken) {
            return { success: false };
        }

        // Try to get a new access token
        const response = await fetch('http://localhost:8000/api/v1/accounts/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh: refreshToken })
        });

        // If the request was successful, update the access token
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('accessToken', data.access);
            return { success: true };
        }

        // If the refresh token is also expired, we need to login again
        return { success: false };
    } catch (error) {
        console.error('Token refresh failed:', error);
        return { success: false };
    }
}

function redirectToLogin() {
    // Clear tokens
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');

    // Redirect to login page
    window.location.href = '/login';
}