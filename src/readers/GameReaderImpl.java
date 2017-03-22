package readers;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

import main.Game;

public class GameReaderImpl implements GameReader {

	private MapReader mapReader;


	public GameReaderImpl(MapReader mapReader) {
		setMapReader(mapReader);
	}

	public MapReader getMapReader() {
		return mapReader;
	}

	public void setMapReader(MapReader mapReader) {
		this.mapReader = mapReader;
	}

	@Override
	public Game readGame(String file) {
		try (BufferedReader br = new BufferedReader(new FileReader(file))) {
			StringBuilder sb = new StringBuilder();
			String line = br.readLine();

			while (line != null) {
				sb.append(line);
				sb.append(System.lineSeparator());
				line = br.readLine();
			}
			String gameData = sb.toString();
			return convertGame(gameData);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			// e.printStackTrace();
			System.out.println(e.getMessage());
			return null;
		}
	}

	@Override
	public Game convertGame(String gameData) {
		Game game = new Game(getMapReader().convertMap(gameData));
		return game;
	}
}
