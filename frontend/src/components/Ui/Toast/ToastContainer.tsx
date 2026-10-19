import { Slide, ToastContainer as Toast } from 'react-toastify';

import 'react-toastify/dist/ReactToastify.css';

export const ToastContainer = () => (
  <Toast
    className="launchpad-toast-container"
    toastClassName="launchpad-toast"
    hideProgressBar
    icon={false}
    closeButton={false}
    transition={Slide}
    theme="dark"
  />
);
