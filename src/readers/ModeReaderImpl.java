package readers;

import java.util.List;

import model.Player;

public class ModeReaderImpl implements ModeReader {

	@Override
	public int readMode(List<Player> players, String gameData) {
		String[] lines = gameData.split(System.lineSeparator());
		for(int i = 0; i < lines.length; i++) {
			String[] values = lines[i].split("=");
			if(values[0].equals("mode")) {
				if(values[1].equals("CLICK")) {
					return 1;
				}
				else if(values[1].equals("CONST")) {
					return 2;
				}
				else if(values[1].equals("FIXED")) {
					return 3;
				}
				else {
					return 1;
				}
			}
		}
		return 1;
	}

}
