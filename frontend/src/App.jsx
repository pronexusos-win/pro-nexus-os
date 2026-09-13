import { useEffect, useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import liff from '@line/liff';

const COMPANY_LIFF_IDS = {
  'pro_nexus': '2011564874-MNIECumQ',
  'tp_extra': '2011576094-vwbg5mee',
  'luck_kio': '2011579873-asAQ8pxU',
  'peak_icon': '2011580328-yWlEyeOK'
};

const TeamUI = () => (
  <div className="p-6">
    <div className="bg-white rounded-2xl shadow-sm border border-indigo-100 p-6 mb-6">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 font-bold text-xl">👥</div>
        <div>
          <h2 className="text-xl font-bold text-gray-800">ระบบจัดการทีม (RBAC)</h2>
          <p className="text-xs text-gray-500">ควบคุมสิทธิ์และโครงสร้างสายงานทีมงาน</p>
        </div>
      </div>
      <div className="border-t border-gray-100 pt-4">
        <p className="text-sm text-gray-600 mb-4">สถานะสิทธิ์ปัจจุบัน: <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded-md font-semibold text-xs">Admin / Member</span></p>
        <div className="bg-gray-50 p-4 rounded-xl text-center text-gray-500 text-sm">
          ยังไม่มีข้อมูลรายชื่อลูกทีมในระบบ
        </div>
      </div>
    </div>
    <div className="text-center">
      <Link to="/" className="inline-block px-6 py-2.5 bg-gray-900 text-white rounded-xl font-medium text-sm shadow hover:bg-gray-800 transition">← กลับหน้าเมนูหลัก</Link>
    </div>
  </div>
);

const ShopUI = () => (
  <div className="p-6">
    <div className="bg-white rounded-2xl shadow-sm border border-emerald-100 p-6 mb-6">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600 font-bold text-xl">🛒</div>
        <div>
          <h2 className="text-xl font-bold text-gray-800">ระบบร้านค้า (Shopping)</h2>
          <p className="text-xs text-gray-500">เลือกซื้อสินค้าและแพ็กเกจระบบ</p>
        </div>
      </div>
      <div className="border-t border-gray-100 pt-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="border border-gray-200 rounded-xl p-3 text-center">
            <div className="h-20 bg-gray-100 rounded-lg mb-2 flex items-center justify-center text-gray-400">📦</div>
            <h3 className="font-bold text-sm text-gray-800">แพ็กเกจเริ่มต้น</h3>
            <p className="text-xs text-emerald-600 font-semibold mt-1">฿990 / เดือน</p>
          </div>
          <div className="border border-gray-200 rounded-xl p-3 text-center">
            <div className="h-20 bg-gray-100 rounded-lg mb-2 flex items-center justify-center text-gray-400">🚀</div>
            <h3 className="font-bold text-sm text-gray-800">แพ็กเกจโปร</h3>
            <p className="text-xs text-emerald-600 font-semibold mt-1">฿2,990 / เดือน</p>
          </div>
        </div>
      </div>
    </div>
    <div className="text-center">
      <Link to="/" className="inline-block px-6 py-2.5 bg-gray-900 text-white rounded-xl font-medium text-sm shadow hover:bg-gray-800 transition">← กลับหน้าเมนูหลัก</Link>
    </div>
  </div>
);

const QrCodeUI = () => (
  <div className="p-6">
    <div className="bg-white rounded-2xl shadow-sm border border-amber-100 p-6 mb-6">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600 font-bold text-xl">📱</div>
        <div>
          <h2 className="text-xl font-bold text-gray-800">ระบบ QR Code</h2>
          <p className="text-xs text-gray-500">สร้างหรือสแกนคิวอาร์โค้ดเพื่อเข้าถึงข้อมูลสายงาน/ชำระเงิน</p>
        </div>
      </div>
      <div className="border-t border-gray-100 pt-4 text-center">
        <div className="w-48 h-48 bg-gray-100 border-2 border-dashed border-gray-300 rounded-2xl mx-auto flex flex-col items-center justify-center p-4 mb-4">
          <span className="text-4xl mb-2">📷</span>
          <p className="text-xs text-gray-500 font-medium">QR Code ประจำตัวของคุณ</p>
        </div>
        <button className="w-full py-3 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-semibold shadow-sm transition">
          สแกน QR Code อื่นๆ
        </button>
      </div>
    </div>
    <div className="text-center">
      <Link to="/" className="inline-block px-6 py-2.5 bg-gray-900 text-white rounded-xl font-medium text-sm shadow hover:bg-gray-800 transition">← กลับหน้าเมนูหลัก</Link>
    </div>
  </div>
);

const SuperAdminUI = () => {
  const [enableReferral, setEnableReferral] = useState(true);
  const [enableMoneyFlow, setEnableMoneyFlow] = useState(false);

  return (
    <div className="p-6">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center text-red-600 font-bold text-xl">⚙️</div>
        <div>
          <h2 className="text-xl font-bold text-gray-800">ตั้งค่าระบบ (Super Admin)</h2>
          <p className="text-xs text-gray-500">ควบคุมระบบหลังบ้านและการกระจายรายได้</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-red-100 p-5 mb-6 space-y-6">
        <div className="flex justify-between items-center">
          <div className="pr-4">
            <h3 className="font-semibold text-gray-800 text-sm">ค่าการแนะนำ (Referral)</h3>
            <p className="text-xs text-gray-400 mt-0.5">เปิด/ปิด โบนัสแนะนำสมาชิกใหม่</p>
          </div>
          <button 
            onClick={() => setEnableReferral(!enableReferral)}
            className={`w-14 h-8 rounded-full transition-colors duration-300 relative focus:outline-none flex-shrink-0 ${enableReferral ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            <span className={`block w-6 h-6 bg-white rounded-full absolute top-1 transition-transform duration-300 shadow-sm ${enableReferral ? 'translate-x-7' : 'translate-x-1'}`}></span>
          </button>
        </div>

        <div className="border-t border-gray-100 pt-4 flex justify-between items-center">
          <div className="pr-4">
            <h3 className="font-semibold text-gray-800 text-sm">เงินไหล/เงินล้น (Money Flow)</h3>
            <p className="text-xs text-gray-400 mt-0.5">เปิด/ปิด การกระจายรายได้แบบ Spillover</p>
          </div>
          <button 
            onClick={() => setEnableMoneyFlow(!enableMoneyFlow)}
            className={`w-14 h-8 rounded-full transition-colors duration-300 relative focus:outline-none flex-shrink-0 ${enableMoneyFlow ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            <span className={`block w-6 h-6 bg-white rounded-full absolute top-1 transition-transform duration-300 shadow-sm ${enableMoneyFlow ? 'translate-x-7' : 'translate-x-1'}`}></span>
          </button>
        </div>
      </div>

      <div className="text-center">
        <Link to="/" className="inline-block px-6 py-2.5 bg-gray-900 text-white rounded-xl font-medium text-sm shadow hover:bg-gray-800 transition">← กลับหน้าเมนูหลัก</Link>
      </div>
    </div>
  );
};

const Home = ({ profile, companyKey }) => (
  <div className="p-6">
    <div className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 rounded-2xl p-4 mb-6 text-center shadow-inner">
      {profile ? (
        <div className="flex items-center space-x-3 text-left">
          <img src={profile.pictureUrl} alt="Profile" className="w-14 h-14 rounded-full border-2 border-white shadow-md flex-shrink-0" />
          <div className="overflow-hidden">
            <h2 className="font-bold text-gray-800 truncate">{profile.displayName}</h2>
            <p className="text-xs text-emerald-600 font-medium">Verified LIFF User</p>
            <span className="inline-block mt-1 px-2 py-0.5 bg-indigo-600 text-white text-[10px] rounded-full uppercase font-semibold">
              {companyKey.replace('_', ' ')}
            </span>
          </div>
        </div>
      ) : (
        <div className="animate-pulse flex items-center space-x-3 text-left">
          <div className="w-14 h-14 bg-gray-200 rounded-full"></div>
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      )}
    </div>

    <div className="grid grid-cols-2 gap-4">
      <Link to="/team" className="bg-white hover:bg-indigo-50/50 border border-gray-100 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all flex flex-col items-center text-center group">
        <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-2xl mb-3 group-hover:scale-110 transition-transform">
          👥
        </div>
        <h3 className="font-bold text-gray-800 text-sm">จัดการทีม</h3>
        <p className="text-[11px] text-gray-400 mt-0.5">RBAC & สมาชิก</p>
      </Link>

      <Link to="/shop" className="bg-white hover:bg-emerald-50/50 border border-gray-100 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all flex flex-col items-center text-center group">
        <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center text-2xl mb-3 group-hover:scale-110 transition-transform">
          🛒
        </div>
        <h3 className="font-bold text-gray-800 text-sm">ระบบร้านค้า</h3>
        <p className="text-[11px] text-gray-400 mt-0.5">ช้อปปิ้งแพ็กเกจ</p>
      </Link>

      <Link to="/qrcode" className="bg-white hover:bg-amber-50/50 border border-gray-100 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all flex flex-col items-center text-center group">
        <div className="w-14 h-14 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center text-2xl mb-3 group-hover:scale-110 transition-transform">
          📱
        </div>
        <h3 className="font-bold text-gray-800 text-sm">QR Code</h3>
        <p className="text-[11px] text-gray-400 mt-0.5">สร้างและสแกน</p>
      </Link>

      <Link to="/admin" className="bg-white hover:bg-red-50/50 border border-red-100 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all flex flex-col items-center text-center group">
        <div className="w-14 h-14 bg-red-50 text-red-600 rounded-2xl flex items-center justify-center text-2xl mb-3 group-hover:scale-110 transition-transform">
          ⚙️
        </div>
        <h3 className="font-bold text-gray-800 text-sm">Super Admin</h3>
        <p className="text-[11px] text-gray-400 mt-0.5">ตั้งค่าระบบหลัก</p>
      </Link>
    </div>
  </div>
);

export default function App() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  const location = useLocation();

  const queryParams = new URLSearchParams(location.search);
  const companyKey = queryParams.get('company') || 'pro_nexus';
  const activeLiffId = COMPANY_LIFF_IDS[companyKey] || COMPANY_LIFF_IDS['pro_nexus'];

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
        <header className="bg-gradient-to-r from-gray-900 to-gray-800 text-white p-4 text-center shadow-md relative flex items-center justify-between">
          <div className="w-6"></div>
          <h1 className="text-lg font-extrabold tracking-tight">Pro Nexus OS</h1>
          <span className="bg-green-500 text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold shadow">
            {companyKey.replace('_', ' ')}
          </span>
        </header>
        {error && <div className="p-3 bg-red-50 text-red-600 text-center border-b border-red-100 text-xs">{error}</div>}
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Home profile={profile} companyKey={companyKey} />} />
            <Route path="/team" element={<TeamUI />} />
            <Route path="/shop" element={<ShopUI />} />
            <Route path="/qrcode" element={<QrCodeUI />} />
            <Route path="/admin" element={<SuperAdminUI />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
