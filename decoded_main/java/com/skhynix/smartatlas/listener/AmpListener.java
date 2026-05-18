package com.skhynix.smartatlas.listener;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.Msg;
import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.util.DataService;

/**
 * A class to communicate with the conveyor server by the socket io.
 * @author 
 *
 */
public class AmpListener {
	private static final Logger logger = LoggerFactory.getLogger(AmpListener.class);
	private String host = "";	
	private int port = 0;

	public AmpListener(String urlString) {
		String[] parts = urlString.replace("http://", "").split(":");        
		this.host = parts[0];
        this.port = Integer.parseInt(parts[1]);
	}
	
	public void start()
	{
		new Thread(() -> {			
			try(Socket socket = new Socket(host, port))
			{
				// 여청 보내기
				OutputStream os = socket.getOutputStream();
				String request = "GET /\n";
				os.write(request.getBytes());
				os.flush();
				
				// response
				InputStream is = socket.getInputStream();
				byte[] buffer = new byte[2048];
				
				int read;
				while((read = is .read(buffer)) != -1) {
					//String response = new String(buffer, 0 , read);
					//logger.info(":::::::::: response:{}", response);
					parseAndPrint(buffer);
				}
			}catch(Exception e)
			{
				e.printStackTrace();
			}
		}).start();
	}
	
	private int parseAndPrint(byte[] data) {
	    int lastProcessedIndex = -1;
	    Msg msg; 
	    		
	    for (int i = 0; i < data.length; i++) {
	        // STX (0x02) 발견
	        if (data[i] == 0x02) {
	            // ETX (0x03) 탐색
	            for (int j = i + 1; j < data.length; j++) {
	                if (data[j] == 0x03) {
	                    // 패킷 추출 (STX와 ETX 사이)
	                    int start = i + 1;
	                    int end = j;
	                    byte[] packetData = new byte[end - start];
	                    System.arraycopy(data, start, packetData, 0, packetData.length);

	                    // 출력
	                    String message = new String(packetData, StandardCharsets.UTF_8);
	                    // fabId는 Worker에서 가져온다
                    	msg = new Msg(
	            				"",
	            				MSG_TYP.AMP,
	            				System.currentTimeMillis(),
	            				"",
	            				message
	            		);
                    	DataService.getInstance().queue.add(msg);
	                    
	                    // 처리된 위치 업데이트 (ETX 까지 처리함)
	                    lastProcessedIndex = j + 1; 
	                    
	                    // 다음 탐색을 위해 i를 j로 이동
	                    i = j; 
	                    break; 
	                }
	            }
	        }
	    }
	    
	    return lastProcessedIndex;
	}	
}
