import React, { useState } from 'react';
import axios from 'axios';

const MpesaCheckoutModal = ({ isOpen, onClose, course, user, appliedDiscount = 0 }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(null); // 'PENDING', 'SUCCESS', 'FAILED'
  const [errorMessage, setErrorMessage] = useState('');

  if (!isOpen) return null;

  const finalPrice = Math.max(0, course.price - appliedDiscount);

  const handleStkPush = async (e) => {
    e.preventDefault();
    setLoading(true);
    setPaymentStatus(null);
    setErrorMessage('');

    // Basic Kenyan phone number validation
    let formattedPhone = phoneNumber.trim();
    if (/^0[17]\d{8}$/.test(formattedPhone)) { formattedPhone = '254' + formattedPhone.substring(1); } else if (!/^254[17]\d{8}$/.test(formattedPhone)) {
      setErrorMessage('Please enter a valid Safaricom phone number (e.g., 0712345678 or 254712345678)');
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post('/api/payments/stk-push', {
        user_id: user.id,
        course_id: course.id,
        phone_number: formattedPhone,
        discount: appliedDiscount
      });

      if (response.data.ResponseCode === '0') {
        setPaymentStatus('PENDING');
        // Optional: Start polling backend transaction status endpoint here if needed,
        // otherwise rely on webhook update or user confirmation screen.
      } else {
        setPaymentStatus('FAILED');
        setErrorMessage(response.data.ResponseDescription || 'Failed to initiate M-Pesa prompt.');
      }
    } catch (err) {
      setPaymentStatus('FAILED');
      setErrorMessage(err.response?.data?.error || 'Network error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md p-6 bg-white rounded-lg shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-gray-900">Complete Enrollment</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">&times;</button>
        </div>

        <div className="mb-4 p-4 bg-gray-50 rounded-md">
          <p className="text-sm font-medium text-gray-700">{course.name}</p>
          <div className="mt-2 flex justify-between text-sm">
            <span className="text-gray-500">Base Price:</span>
            <span className="font-semibold">KES {course.price.toLocaleString()}</span>
          </div>
          {appliedDiscount > 0 && (
            <div className="flex justify-between text-sm text-green-600">
              <span>Admin Discount:</span>
              <span>- KES {appliedDiscount.toLocaleString()}</span>
            </div>
          )}
          <div className="mt-2 pt-2 border-t border-gray-200 flex justify-between text-base font-bold text-gray-900">
            <span>Total Payable:</span>
            <span className="text-indigo-600">KES {finalPrice.toLocaleString()}</span>
          </div>
        </div>

        {paymentStatus === 'PENDING' ? (
          <div className="text-center py-6">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <h4 className="text-lg font-medium text-gray-900">Check your phone</h4>
            <p className="text-sm text-gray-500 mt-1">
              An M-Pesa STK push prompt has been sent to <strong>{phoneNumber}</strong>. Enter your PIN to complete payment.
            </p>
          </div>
        ) : (
          <form onSubmit={handleStkPush}>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">M-Pesa Phone Number</label>
              <input
                type="text"
                placeholder="0712345678"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>

            {errorMessage && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-md">
                {errorMessage}
              </div>
            )}

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 text-sm font-medium text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Processing...' : `Pay KES ${finalPrice.toLocaleString()}`}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default MpesaCheckoutModal;
