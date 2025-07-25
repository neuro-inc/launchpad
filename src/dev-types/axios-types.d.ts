import 'axios';

declare module 'axios' {
  export interface AxiosRequestConfig {
    formatResponse?: boolean;
    formatResponseLevel?: number;
    sentryIgnoreCodes?: number | number[];
  }
}
