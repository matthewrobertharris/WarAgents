package main;

import javax.swing.JFrame;

import model.Map;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class Game {

	public static final int SQUARE_SIZE = 20;
	public static final int RANDOM_SEED = 1;
	public static final String FILE = "resources\\test\\basic.map";
	private Map map;

	public Game(Map map) {
		setMap(map);
	}

	public static void main(String[] args) {

		GameReader gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		Game game = gameReader.readGame(FILE);
		if (game != null) {
			game.run();
		}

	}

	public void run() {
		System.out.println(getMap().toString());
		TreeRenderer renderer = new TreeRenderer(getMap());
		JFrame frame = new JFrame("WarAgents");
		frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
		frame.add(renderer);
		frame.setSize(20 * SQUARE_SIZE, 20 * SQUARE_SIZE);
		frame.setLocationRelativeTo(null);
		frame.setVisible(true);
		renderer.setFrame(frame);
	}

	public Map getMap() {
		return map;
	}

	public void setMap(Map map) {
		this.map = map;
	}

}
