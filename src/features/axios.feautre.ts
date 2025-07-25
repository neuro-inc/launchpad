import axios from 'axios';

import { SERVER_API_URL } from '@constants';
import { formatToCamelCase } from '@utils/formatters';

const instance = axios.create({
  baseURL: SERVER_API_URL,
  withCredentials: true,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/json',
  },
});

instance.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => Promise.reject(error),
);

instance.interceptors.response.use(
  ({ data, config: { formatResponse = true, formatResponseLevel } }) =>
    formatResponse
      ? (formatToCamelCase(data, formatResponseLevel) as any)
      : data,
  (error) => {
    const { response = {} } = error;

    return Promise.reject(response.data ?? response);
  },
);

export default instance;
