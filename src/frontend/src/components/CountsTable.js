import React, { useRef, useEffect } from 'react';

const CountsTable = () => {
  const tableRef = useRef(null);
  
  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const response = await fetch('http://localhost:8000/redis/counts');
        const result = await response.json();
        
        // Only update table when we have success:true AND actual data
        if (result.success && result.data) {
          updateTableCells(result.data);
        }
        // If success:false, it means no NEW data available - don't update table (keep current values)
        // This prevents showing zeros when no new data is available
      } catch (error) {
        // Silently handle network errors - don't update table on errors
        console.debug('Error fetching counts:', error);
      }
    };

    const updateTableCells = (data) => {
      if (!tableRef.current) return;
      
      const cells = tableRef.current.querySelectorAll('td');
      
      if (data) {
        // Row 1: Raw counts
        cells[0].textContent = data.alice_singles.toLocaleString();
        cells[1].textContent = data.bob_singles.toLocaleString();
        cells[2].textContent = data.coincidences.toLocaleString();
        
        // Row 2: Efficiencies
        cells[3].textContent = data.alice_efficiency;
        cells[4].textContent = data.bob_efficiency;
        cells[5].textContent = data.joint_efficiency;
      } else {
        // No data - show zeros
        for (let i = 0; i < 6; i++) {
          cells[i].textContent = '0';
        }
      }
    };

    // Initial fetch
    fetchCounts();

    // Set up polling every 200ms
    const interval = setInterval(fetchCounts, 200);

    return () => clearInterval(interval);
  }, []);

  return (
    <table 
      ref={tableRef}
      style={{
        width: '100%',
        borderCollapse: 'collapse',
        backgroundColor: 'white',
        fontSize: '24pt',
        fontFamily: 'Arial, sans-serif'
      }}
    >
      <thead>
        <tr>
          <th style={{
            backgroundColor: '#ecf0f1',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24pt',
            fontWeight: 'normal'
          }}>
            Alice
          </th>
          <th style={{
            backgroundColor: '#ecf0f1',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24pt',
            fontWeight: 'normal'
          }}>
            Bob
          </th>
          <th style={{
            backgroundColor: '#ecf0f1',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24pt',
            fontWeight: 'normal'
          }}>
            Coinc
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style={{
            backgroundColor: 'white',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24px'
          }}>
            0
          </td>
          <td style={{
            backgroundColor: 'white',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24px'
          }}>
            0
          </td>
          <td style={{
            backgroundColor: 'white',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24px'
          }}>
            0
          </td>
        </tr>
        <tr>
          <td style={{
            backgroundColor: 'white',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24px'
          }}>
            0
          </td>
          <td style={{
            backgroundColor: 'white',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24px'
          }}>
            0
          </td>
          <td style={{
            backgroundColor: 'white',
            color: 'black',
            padding: '12px',
            textAlign: 'center',
            border: '0.5px solid black',
            fontSize: '24px'
          }}>
            0
          </td>
        </tr>
      </tbody>
    </table>
  );
};

export default CountsTable;