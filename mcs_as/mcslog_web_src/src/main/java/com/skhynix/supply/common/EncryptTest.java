package com.skhynix.supply.common;

import org.jasypt.encryption.pbe.StandardPBEStringEncryptor;

public class EncryptTest {
	
	//private static final String ENCRYPT_KEY = "bngSys";
	
	public static void main(String[] args) {
		
		try {
			StandardPBEStringEncryptor  encryptor = new StandardPBEStringEncryptor();
			encryptor.setAlgorithm("PBEWithMD5AndDES");  
			//encryptor.setPassword(ENCRYPT_KEY);
			encryptor.setPassword("bngSys");
			String encryptedPass = encryptor.encrypt("10.192.227.59");
			System.out.println("encryptedPass : " + encryptedPass);
			System.out.println("decryptedPass : " +  encryptor.decrypt(encryptedPass));
			System.out.println("decryptedPassRaw : " +  encryptor.decrypt("vqCjqeMHr6xCDeSjzjhAxmTIS7GLJc6r"));
		} catch (Exception e) {
			// TODO: handle exception
		}
	}
	
}
