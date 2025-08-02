importScripts('https://www.gstatic.com/firebasejs/9.6.11/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.6.11/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyAY3N3Ekmj_drw3P2QlsyyWiW1OPkG0jxU",
    authDomain: "forrent-b4654.firebaseapp.com",
    projectId: "forrent-b4654",
    storageBucket: "forrent-b4654.appspot.com",
    messagingSenderId: "603917507536",
    appId: "1:603917507536:web:5fc141d950fc1f4f9237d5",
    measurementId: "G-C6RHS2PC3L"
});

const messaging = firebase.messaging();

// Background notifications
messaging.onBackgroundMessage((payload) => {
    console.log('Background message received ', payload);
    const { title, body } = payload.notification;
    self.registration.showNotification(title, { body });
});
