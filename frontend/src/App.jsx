import { useEffect, useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import liff from '@line/liff';

const COMPANY_LIFF_IDS = {
  'PN': '2011564874-MNIECumQ',
  'TP_EXTRA': '2011576094-vwbg5mee',
  'LUCK_KIO': '2011579873-asAQ8pxU',
  'PEAK_ICON': '2011580328-yWlEyeOK'
};

const TeamUI = () => <div className="p-8 text-center"><h2 className="text-2xl font-bold mb-4">จัดการทีม (RBAC)</h2><Link to="/" className="text-blue-500 underline">กลับหน้าแรก</Link></div>;
const ShopUI = () => <div className="p-8 text-center"><h2 className="text-2xl font-bold mb-4">ระบบร้านค้า</h2><Link to="/" className="text-blue-500 underline">กลับหน้าแรก</Link></div>;
const OcrUI = () => <div className="p-8 text-center"><h2 className="text-2xl font-bold mb-4">สแกนเอกสาร (OCR)</h2><Link to="/" className="text-blue-500 underline">กลับหน้าแรก</Link></div>;

// หน้าจอตั้งค่าสำหรับ Super Admin
const SuperAdminUI = () => {
  const [enableReferral, setEnableReferral] = useState(true);
  const [enableMoneyFlow, setEnableMoneyFlow] = useState(false);

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">ตั้งค่าระบบ (Super Admin)</h2>
      
      <div className="bg-white rounded-xl shadow-md border border-gray-100 p-5 mb-6">
        
        {/* สวิตช์ เปิด-ปิด ระบบแนะนำ */}
        <div className="flex justify-between items-center mb-6 border-b border-gray-100 pb-4">
          <div className="pr-4">
            <h3 className="font-semibold text-gray-700 text-lg">ค่าการแนะนำ (Referral)</h3>
            <p className="text-xs text-gray-500 mt-1">เปิด/ปิด การจ่ายโบนัสแนะนำสมาชิกใหม่</p>
          </div>
          <button 
            onClick={() => setEnableReferral(!enableReferral)}
            className={`w-14 h-8 rounded-full transition-colors duration-300 relative focus:outline-none flex-shrink-0 ${enableReferral ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            <span className={`block w-6 h-6 bg-white rounded-full absolute top-1 transition-transform duration-300 shadow-sm ${enableReferral ? 'translate-x-7' : 'translate-x-1'}`}></span>
          </button>
        </div>

        {/* สวิตช์ เปิด-ปิด ระบบเงินไหล/เงินล้น */}
        <div className="flex justify-between items-center">
          <div className="pr-4">
            <h3 className="font-semibold text-gray-700 text-lg">เงินไหล/เงินล้น (Money Flow)</h3>
            <p className="text-xs text-gray-500 mt-1">เปิด/ปิด การกระจายรายได้แบบ Spillover</p>
          </div>
          <button 
            onClick={() => setEnableMoneyFlow(!enableMoneyFlow)}
            className={`w-14 h-8 rounded-full transition-colors duration-300 relative focus:outline-none flex-shrink-0 ${enableMoneyFlow ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            <span className={`block w-6 h-6 bg-white rounded-full absolute top-1 transition-transform duration-300 shadow-sm ${enableMoneyFlow ? 'translate-x-7' : 'translate-x-1'}`}></span>
          </button>
        </div>
      </div>

      <div className="text-center mt-8">
        <Link to="/" className="text-blue-600 hover:text-blue-800 font-medium underline">กลับหน้าเมนูหลัก</Link>
      </div>
    </div>
  );
};

const Home = ({ profile, companyName }) => (
  <div className="p-6">
    <div className="text-center mb-8">
      {profile ? (
        <div className="animate-fade-in">
          <img src={profile.pictureUrl} alt="Profile" className="w-24 h-24 rounded-full mx-auto border-4 border-indigo-100 shadow-lg mb-3" />
          <h2 className="text-xl font-bold text-gray-800">{profile.displayName}</h2>
          <p className="text-sm text-green-600 font-medium">ยืนยันตัวตนสำเร็จ</p>
        </div>
      ) : (
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-24 h-24 bg-gray-200 rounded-full mb-3"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      )}
    </div>

    <div className="grid grid-cols-1 gap-4">
      <Link to="/team" className="bg-indigo-600 hover:bg-indigo-700 text-white text-center py-4 rounded-xl shadow-md font-semibold transition-all">ระบบจัดการทีม (Team UI)</Link>
      <Link to="/shop" className="bg-emerald-500 hover:bg-emerald-600 text-white text-center py-4 rounded-xl shadow-md font-semibold transition-all">ระบบร้านค้า (Shopping)</Link>
      <Link to="/ocr" className="bg-violet-500 hover:bg-violet-600 text-white text-center py-4 rounded-xl shadow-md font-semibold transition-all">สแกนเอกสาร (OCR)</Link>
      {/* เพิ่มปุ่ม Super Admin */}
      <Link to="/admin" className="bg-red-500 hover:bg-red-600 text-white text-center py-4 rounded-xl shadow-md font-semibold transition-all mt-4 border-2 border-red-300">ตั้งค่า Super Admin</Link>
    </div>
  </div>
);

export default function App() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  const location = useLocation();

  // ดึงชื่อบริษัทจาก URL (เช่น ?company=TP_EXTRA) 
  // ถ้าเข้าลิงก์เพียวๆ ไม่มี ?company=... จะตั้งค่าให้ Pro Nexus (PN) เป็นบริษัทเริ่มต้นทันที!
  const queryParams = new URLSearchParams(location.search);
  const companyKey = queryParams.get('company') || 'PN';
  const activeLiffId = COMPANY_LIFF_IDS[companyKey] || COMPANY_LIFF_IDS['PN'];

  useEffect(() => {
    liff.init({ liffId: activeLiffId })
      .then(() => {
        if (!liff.isLoggedIn()) {
          liff.login();
        } else {
          liff.getProfile().then(setProfile).catch(err => setError("ดึงข้อมูลไม่ได้: " + err.message));
        }
      })
      .catch(err => setError("LIFF Init Error: " + err.message));
  }, [activeLiffId]);

  return (
    <div className="min-h-screen bg-gray-100 font-sans flex justify-center">
      <div className="w-full max-w-md bg-white shadow-2xl min-h-screen flex flex-col">
        <header className="bg-gradient-to-r from-gray-900 to-gray-800 text-white p-5 text-center shadow-md relative">
          <h1 className="text-2xl font-extrabold tracking-tight">Pro Nexus OS</h1>
          <span className="absolute top-2 right-2 bg-green-500 text-xs px-2 py-1 rounded-full shadow">{companyKey.replace('_', ' ')}</span>
        </header>
        
        {error && <div className="p-4 bg-red-50 text-red-600 text-center border-b border-red-100 text-sm">{error}</div>}
        
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Home profile={profile} companyName={companyKey} />} />
            <Route path="/team" element={<TeamUI />} />
            <Route path="/shop" element={<ShopUI />} />
            <Route path="/ocr" element={<OcrUI />} />
            {/* เส้นทางไปหน้าตั้งค่า Super Admin */}
            <Route path="/admin" element={<SuperAdminUI />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
