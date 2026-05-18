package com.skhynix.smartatlas.util;

import java.security.Security;
import java.util.Base64;
import java.util.Base64.Decoder;
import java.util.Base64.Encoder;

import javax.crypto.BadPaddingException;
import javax.crypto.Cipher;
import javax.crypto.IllegalBlockSizeException;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.bouncycastle.jce.provider.BouncyCastleProvider;

public class CryptoUtil {
	static {
		Security.addProvider(new BouncyCastleProvider());
	}
	
	public static String encrypt(String target, String key) {
		SecretKeySpec keySpec = null;
		String newKey = "";		
		while(newKey.getBytes().length < 32) {
			newKey+=key;
		}
		byte[] k = newKey.substring(0, 32).getBytes();
		keySpec = new SecretKeySpec(k, "AES");
		Cipher cipher = null;
		try {
			cipher = Cipher.getInstance("AES/GCM/NoPadding", "BC");
		} catch (Exception e) {
			return null;
		}
		
		try {
			cipher.init(Cipher.ENCRYPT_MODE, keySpec, new IvParameterSpec(newKey.substring(0, 32).getBytes()));
		} catch (Exception e) {
			return null;
		}
		
		try {
			Encoder encoder = Base64.getEncoder();
			return new String(encoder.encode(cipher.doFinal(target.getBytes())));
		} catch (IllegalBlockSizeException e) {
			
		} catch (BadPaddingException e) {
			
		}
		return null;
	}
	
	public static String decrypt(String target, String key) {
		SecretKeySpec keySpec = null;
		String newKey = "";		
		while(newKey.getBytes().length < 32) {
			newKey+=key;
		}
		byte[] k = newKey.substring(0, 32).getBytes();
		keySpec = new SecretKeySpec(k, "AES");
		Cipher cipher = null;
		try {
			cipher = Cipher.getInstance("AES/GCM/NoPadding", "BC");
		} catch (Exception e) {
			return null;
		}
		
		try {
			cipher.init(Cipher.DECRYPT_MODE, keySpec, new IvParameterSpec(newKey.substring(0, 32).getBytes()));
		} catch (Exception e) {
			
			return null;
		}
		
		try {
			Decoder decoder = Base64.getDecoder();
			return new String(cipher.doFinal(decoder.decode(target.getBytes())));
		} catch (IllegalBlockSizeException e) {
			System.out.println("err");
		} catch (IllegalArgumentException e) {
		} catch (BadPaddingException e) {}
		return null;
	}
}
