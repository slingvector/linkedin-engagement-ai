const axios = require('axios');
console.log(axios.getUri({ baseURL: '/api/v1', url: '/v2/posts/123/carousel' }));
console.log(axios.getUri({ baseURL: '/api/v1', url: 'v2/posts/123/carousel' }));
console.log(axios.getUri({ baseURL: 'http://localhost:3000/api/v1', url: '/v2/posts/123/carousel' }));
