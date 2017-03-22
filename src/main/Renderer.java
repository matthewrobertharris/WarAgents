package main;

import java.awt.Color;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.event.WindowEvent;

import javax.swing.JFrame;
import javax.swing.JPanel;

import model.Map;
import model.Tile;

public class Renderer extends JPanel {

	public static final int WAIT_TIME = 1000;
	private Map map;
	private JFrame frame;
	private int time;
	private int mode;

	private static final long serialVersionUID = 1L;

	public Renderer(Map map, int mode) {
		super();
		setMap(map);
		setTime(0);
		setMode(mode);
		addMouseListener(new MouseAdapter() {
			public void mousePressed(MouseEvent me) {
				if (getMode() == 1) {
					update();
				} else {
					run();
				}
			}
		});
	}

	public void run() {
		while (true) {
			if (getMode() == 2) {
				update();
			} else if (getMode() == 3) {
				try {
					Thread.sleep(WAIT_TIME); // 1000 milliseconds is one second.
					update();
				} catch (InterruptedException ex) {
					System.out.println("Thread interrupted");
					closeFrame();
				}
			}
		}
	}

	public void closeFrame() {
		getFrame().dispatchEvent(new WindowEvent(getFrame(), WindowEvent.WINDOW_CLOSING));
	}

	public void update() {
		setTime(getTime() + 1);
		try {
			if (getMap().update()) {
				System.out.println("WINNER");
				closeFrame();
			}
		} catch (Exception e) {
			e.printStackTrace(System.out);
			//System.out.println("Renderer Exception:\n " + e.getMessage() + "\n");
			closeFrame();
		}
		//System.out.println(getMap().printAgents());
		// System.out.println(getMap().printFood());
		getFrame().repaint();
	}

	public int getMode() {
		return mode;
	}

	public void setMode(int mode) {
		this.mode = mode;
	}

	public int getTime() {
		return time;
	}

	public void setTime(int time) {
		this.time = time;
	}

	public Map getMap() {
		return map;
	}

	public void setMap(Map map) {
		this.map = map;
	}

	public JFrame getFrame() {
		return frame;
	}

	public void setFrame(JFrame frame) {
		this.frame = frame;
	}

	public static long getSerialversionuid() {
		return serialVersionUID;
	}

	public void paintComponent(Graphics g) {
		super.paintComponent(g);
		Graphics2D g2d = (Graphics2D) g;
		Map map = getMap();

		for (int y = 0; y < map.getHeight(); y++) {
			for (int x = 0; x < map.getWidth(); x++) {
				Tile tile = map.getTile(x, y);
				if (tile.isOccupied()) {
					g2d.setColor(new Color(0, 0, 255));
					g2d.fillRect(x * Game.SQUARE_SIZE, y * Game.SQUARE_SIZE, Game.SQUARE_SIZE, Game.SQUARE_SIZE);
				} else {
					if (tile.getPlant() != null) {
						g2d.setColor(new Color(0, 255, 0));
						g2d.fillRect(x * Game.SQUARE_SIZE, y * Game.SQUARE_SIZE, Game.SQUARE_SIZE, Game.SQUARE_SIZE);
					} else {
						g2d.setColor(new Color(getHeightColour(tile), getFoodColour(tile), 0));
						g2d.fillRect(x * Game.SQUARE_SIZE, y * Game.SQUARE_SIZE, Game.SQUARE_SIZE, Game.SQUARE_SIZE);
					}
				}
			}
		}
	}

	public int getHeightColour(Tile tile) {
		return getColour(tile.getDirt(), Tile.MIN_DIRT, Tile.MAX_DIRT);
	}

	public int getFoodColour(Tile tile) {
		return getColour(tile.getFood(), Tile.MIN_FOOD, Tile.MAX_FOOD);
	}

	public int getColour(int value, int min, int max) {
		int range = max - min;
		value += min;
		int colour = (int) ((1.0 * value / range) * 255);
		if (colour > 255) {
			colour = 255;
		}
		return colour;
	}
}