
import './ErrorMessage.css';

const ErrorMessage = ({ message }) => {
  return (
    <div className="error-message">
      <p className="error-text">{message}</p>
    </div>
  );
};

export default ErrorMessage;
