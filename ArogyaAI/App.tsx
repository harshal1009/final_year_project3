import AsyncStorage from '@react-native-async-storage/async-storage';

const API_URL = "http://192.168.56.1:8000";

import {Text,View,Button,TextInput,Image,ScrollView,KeyboardAvoidingView,Platform,TouchableOpacity,
} from 'react-native';

import { useState } from 'react';
import * as ImagePicker from 'expo-image-picker';

export default function App() {
const [screen, setScreen] = useState<'auth' | 'home' | 'chat' | 'emergency'>('auth');

  const [message, setMessage] = useState('');
  const [chat, setChat] = useState<any[]>([]);
  const [image, setImage] = useState<string | null>(null);
   const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

const sendMessage = async () => {
  // Check if at least message or image exists
  if (!message.trim() && !image) {
    alert('Please enter a message or select an image');
    return;
  }

  setLoading(true);

  // show user message in UI
  if (message.trim()) {
    setChat((prev) => [...prev, { type: 'text', value: message, sender: 'user' }]);
  }

  const token = await AsyncStorage.getItem('token');

  const formData = new FormData();
  
  // Only append message if it's not empty
  if (message.trim()) {
    formData.append('message', message.trim());
  }

  if (image) {
    formData.append('image', {
      uri: image,
      name: 'upload.jpg',
      type: 'image/jpeg',
    } as any);
  }

  setMessage('');
  setImage(null);

  try {
    const res = await fetch(`${API_URL}/chat/send`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    setLoading(false);

    if (!res.ok) {
      const errorData = await res.json();
      setChat((prev) => [
        ...prev,
        { type: 'text', value: `Error: ${errorData.detail || 'Authentication failed'}`, sender: 'ai' },
      ]);
      return;
    }

    const data = await res.json();
    console.log('Response data:', data);

    setChat((prev) => [
      ...prev,
      { type: 'text', value: data.reply, sender: 'ai' },
    ]);
  } catch (error) {
    setLoading(false);
    console.log('Error:', error);
    setChat((prev) => [
      ...prev,
      { type: 'text', value: 'Server not reachable', sender: 'ai' },
    ]);
  }
};



const pickImage = async () => {
 const result = await ImagePicker.launchImageLibraryAsync({
  quality: 0.5,
});

  if (!result.canceled) {
    const uri = result.assets[0].uri;
    setImage(uri);

    // show image in chat immediately
    setChat((prev) => [
      ...prev,
      { type: 'image', value: uri, sender: 'user' },
    ]);
  }
};

  if (screen === 'auth') {

 

  const signup = async () => {
    try {
      const res = await fetch(`${API_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        alert('Signup failed');
        return;
      }

      alert('Signup successful, please login');
    } catch {
      alert('Server not reachable');
    }
  };

  const login = async () => {
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        alert('Invalid credentials');
        return;
      }

      const data = await res.json();
      await AsyncStorage.setItem('token', data.access_token);

      setScreen('home');
    } catch {
      alert('Server not reachable');
    }
  };

  return (
      <View style={{ flex: 1, justifyContent: 'center', padding: 20 }}>
        <Text style={{ fontSize: 26, textAlign: 'center', marginBottom: 30 }}>
          ArogyaAI
        </Text>

        <TextInput
          placeholder="Email"
          value={email}
          onChangeText={setEmail}
          style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
        />

        <TextInput
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          style={{ borderWidth: 1, padding: 10, marginBottom: 20 }}
        />

        <Button title="Login" onPress={login} />
        <View style={{ height: 10 }} />
        <Button title="Sign Up" onPress={signup} />
      </View>
    );
  
}



  if (screen === 'chat') {
  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={{ flex: 1, padding: 10 }}>
        <Text style={{ fontSize: 20, textAlign: 'center', marginBottom: 10 }}>
          Chat
        </Text>

        <ScrollView style={{ flex: 1 }} keyboardShouldPersistTaps="handled">
          {chat.map((item, index) => (
            <View
              key={index}
              style={{
                alignSelf: item.sender === 'user' ? 'flex-end' : 'flex-start',
                backgroundColor: item.sender === 'user' ? '#dcf8c6' : '#e6f2ff',
                padding: 8,
                borderRadius: 6,
                marginBottom: 8,
                maxWidth: '80%',
              }}
            >
              {item.type === 'text' && <Text>{item.value}</Text>}
              {item.type === 'image' && (
                <Image
                  source={{ uri: item.value }}
                  style={{ width: 150, height: 150 }}
                />
              )}
            </View>
          ))}
          {loading && (
            <View style={{ alignSelf: 'flex-start', padding: 8 }}>
              <Text style={{ color: 'gray' }}>AI is thinking...</Text>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            marginTop: 5,
          }}
        >
          <TextInput
            placeholder="Type message..."
            value={message}
            onChangeText={setMessage}
            style={{
              flex: 1,
              borderWidth: 1,
              borderRadius: 5,
              padding: 8,
              marginRight: 5,
            }}
          />

          <TouchableOpacity onPress={sendMessage} disabled={loading}>
            <Text style={{ padding: 8, color: loading ? 'gray' : 'blue' }}>
              {loading ? 'Sending...' : 'Send'}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Button title="Send Image" onPress={pickImage} disabled={loading} />
          <Button title="Go Back" onPress={() => setScreen('home')} disabled={loading} />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}


  if (screen === 'emergency') {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <Text>Emergency Screen</Text>
        <Button title="Go Back" onPress={() => setScreen('home')} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text style={{ fontSize: 24, marginBottom: 20 }}>ArogyaAI</Text>
      <Button title="Chat" onPress={() => setScreen('chat')} />
      <Button title="Emergency" onPress={() => setScreen('emergency')} />
    </View>
  );
}