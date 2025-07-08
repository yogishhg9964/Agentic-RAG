import React from 'react';
// import { fetchDebugInfo } from '../api'; // If you create a backend endpoint for this

function DebugInfoView() {
  // const [debugInfo, setDebugInfo] = useState('Loading debug information...');

  // useEffect(() => {
  //   const getDebugInfo = async () => {
  //     try {
  //       // const data = await fetchDebugInfo(); // Assuming you might add this API call
  //       // setDebugInfo(data.log || 'No debug information available.');
  //       setDebugInfo('Debug information will be shown here. Currently, backend logs to server console.');
  //     } catch (error) {
  //       console.error("Error fetching debug info:", error);
  //       setDebugInfo('Failed to load debug information.');
  //     }
  //   };
  //   getDebugInfo();
  // }, []);

  return (
    <div className="debug-info-view">
      <h2>Debug Information</h2>
      <p>For detailed debug logs, please check the backend server console.</p>
      <p>The backend API is expected to be running at: <code>{process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001/api'}</code></p>
      {/* <pre>{debugInfo}</pre> */}
    </div>
  );
}

export default DebugInfoView;
