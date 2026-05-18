import React from 'react';

export default function Stepper({ currentStep }) {
  const steps = [
    { id: 1, label: 'Upload' },
    { id: 2, label: 'Audit Summary' },
    { id: 3, label: 'Export' },
  ];

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 32, gap: 16 }}>
      {steps.map((step, index) => {
        const isCompleted = currentStep > step.id;
        const isActive = currentStep === step.id;
        
        let nodeStyle = {
          width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 600, border: '2px solid'
        };
        
        if (isCompleted) {
          nodeStyle = { ...nodeStyle, borderColor: 'var(--accent)', background: 'var(--accent)', color: '#fff' };
        } else if (isActive) {
          nodeStyle = { ...nodeStyle, borderColor: 'var(--accent)', background: 'var(--bg-white)', color: 'var(--accent)' };
        } else {
          nodeStyle = { ...nodeStyle, borderColor: 'var(--border)', background: 'var(--bg-white)', color: 'var(--text-muted)' };
        }

        return (
          <React.Fragment key={step.id}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={nodeStyle}>
                {isCompleted ? '✓' : step.id}
              </div>
              <span style={{ 
                fontSize: 13, 
                fontWeight: isActive ? 600 : 500,
                color: (isActive || isCompleted) ? 'var(--text-primary)' : 'var(--text-muted)'
              }}>
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div style={{ 
                height: 2, width: 40, 
                background: isCompleted ? 'var(--accent)' : 'var(--border)',
                opacity: 0.5
              }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
